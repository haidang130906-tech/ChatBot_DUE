from collections import OrderedDict
from datetime import datetime, timedelta
import re
import time

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, Range, SearchParams
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Đọc file .env (đặt cùng thư mục với file này)
load_dotenv()

# ====================== CONFIG ======================
QDRANT_HOST      = "localhost"
QDRANT_PORT      = 6333
COLLECTION_NAME  = "due"

EMBED_MODEL_NAME = "intfloat/multilingual-e5-large"

TOP_K            = 10      # số kết quả trả về cuối cùng
MAX_CHARS        = 800    # giới hạn ký tự mỗi chunk đưa vào prompt

# --- Google Gemini API (free tier) ---
# Lấy API key tại: https://aistudio.google.com/app/apikey
# Đặt key vào file .env: GOOGLE_API_KEY=your_key_here
GEMINI_MODEL     = "gemini-2.5-flash"   # free tier, ~10 RPM / 250 RPD
MAX_TOKENS       = 1024

# --- Qdrant performance (quan trọng khi có 50k+ vectors) ---
HNSW_EF          = 64     # giảm từ 128 → 64 để tăng tốc; tăng lên nếu cần chính xác hơn
OVERSAMPLE_FACTOR = 3     # lấy dư khi cần re-sort theo ngày (sort_newest)

MAX_CACHE_SIZE   = 100

# ====================== INIT ======================
print("📦 Đang khởi tạo...")

# Cấu hình Gemini API key
_api_key = os.getenv("GOOGLE_API_KEY")
if not _api_key:
    raise EnvironmentError(
        "❌ Chưa đặt GOOGLE_API_KEY.\n"
        "   Lấy key tại: https://aistudio.google.com/app/apikey\n"
        "   Sau đó thêm vào file .env: GOOGLE_API_KEY=your_key_here"
    )
genai.configure(api_key=_api_key)
gemini_model = genai.GenerativeModel(GEMINI_MODEL)

embed_model = SentenceTransformer(EMBED_MODEL_NAME, device="cpu")
qdrant      = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
cache       = OrderedDict()

print("✅ Sẵn sàng!\n")


# ====================== DATE PARSING ======================

def parse_date_filter(query: str) -> dict:
    """
    Phân tích query để tìm điều kiện thời gian bằng tiếng Việt.

    Nhận diện:
      - mới nhất / gần đây        → sắp xếp theo ngày mới nhất (không filter)
      - hôm nay / hôm qua         → ngày cụ thể
      - tuần này / tuần trước     → khoảng tuần
      - X ngày qua                → N ngày gần đây
      - tháng này / tháng trước   → khoảng tháng
      - X tháng qua               → N tháng gần đây
      - năm nay / năm ngoái       → khoảng năm
      - tháng X/YYYY              → tháng cụ thể
      - DD/MM/YYYY                → ngày cụ thể

    Returns dict:
        date_from   : datetime | None
        date_to     : datetime | None
        sort_newest : bool
        label       : str
    """
    now         = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    q           = query.lower()

    result = {"date_from": None, "date_to": None, "sort_newest": False, "label": ""}

    if re.search(r"mới nhất|gần đây|mới cập nhật|cập nhật mới|tin mới", q):
        result["sort_newest"] = True
        result["label"] = "thông tin mới nhất"
        return result

    if re.search(r"hôm nay|ngày hôm nay|ngày này", q):
        result["date_from"] = today_start
        result["date_to"]   = now
        result["label"]     = f"hôm nay ({today_start.strftime('%d/%m/%Y')})"
        return result

    if re.search(r"hôm qua|ngày hôm qua|ngày qua", q):
        yesterday = today_start - timedelta(days=1)
        result["date_from"] = yesterday
        result["date_to"]   = today_start - timedelta(seconds=1)
        result["label"]     = f"hôm qua ({yesterday.strftime('%d/%m/%Y')})"
        return result

    if re.search(r"tuần này|tuần hiện tại", q):
        start_of_week = today_start - timedelta(days=today_start.weekday())
        result["date_from"] = start_of_week
        result["date_to"]   = now
        result["label"]     = (
            f"tuần này ({start_of_week.strftime('%d/%m')} – {now.strftime('%d/%m/%Y')})"
        )
        return result

    if re.search(r"tuần trước|tuần vừa rồi|tuần vừa qua", q):
        start_of_week   = today_start - timedelta(days=today_start.weekday())
        end_last_week   = start_of_week - timedelta(seconds=1)
        start_last_week = start_of_week - timedelta(days=7)
        result["date_from"] = start_last_week
        result["date_to"]   = end_last_week
        result["label"]     = (
            f"tuần trước ({start_last_week.strftime('%d/%m')} – {end_last_week.strftime('%d/%m/%Y')})"
        )
        return result

    m = re.search(r"(\d+)\s*ngày\s*(qua|gần đây|trước|vừa qua)", q)
    if m:
        n_days = int(m.group(1))
        result["date_from"] = today_start - timedelta(days=n_days)
        result["date_to"]   = now
        result["label"]     = f"{n_days} ngày gần đây"
        return result

    if re.search(r"tháng này|tháng hiện tại", q):
        start_of_month = today_start.replace(day=1)
        result["date_from"] = start_of_month
        result["date_to"]   = now
        result["label"]     = f"tháng này (tháng {now.month}/{now.year})"
        return result

    if re.search(r"tháng trước|tháng vừa rồi|tháng vừa qua", q):
        if now.month == 1:
            lm_year, lm_month = now.year - 1, 12
        else:
            lm_year, lm_month = now.year, now.month - 1
        start_last_month = datetime(lm_year, lm_month, 1)
        start_this_month = today_start.replace(day=1)
        result["date_from"] = start_last_month
        result["date_to"]   = start_this_month - timedelta(seconds=1)
        result["label"]     = f"tháng trước (tháng {lm_month}/{lm_year})"
        return result

    m = re.search(r"(\d+)\s*tháng\s*(qua|gần đây|trước|vừa qua)", q)
    if m:
        n_months = int(m.group(1))
        result["date_from"] = today_start - timedelta(days=n_months * 30)
        result["date_to"]   = now
        result["label"]     = f"{n_months} tháng gần đây"
        return result

    if re.search(r"năm ngoái|năm trước", q):
        last_year = now.year - 1
        result["date_from"] = datetime(last_year, 1, 1)
        result["date_to"]   = datetime(last_year, 12, 31, 23, 59, 59)
        result["label"]     = f"năm {last_year}"
        return result

    if re.search(r"năm nay|năm hiện tại", q):
        result["date_from"] = datetime(now.year, 1, 1)
        result["date_to"]   = now
        result["label"]     = f"năm {now.year}"
        return result

    m = re.search(r"tháng\s*(\d{1,2})[/\s\-]+(\d{4})", q)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            start = datetime(year, month, 1)
            end   = datetime(year, 12, 31, 23, 59, 59) if month == 12 \
                    else datetime(year, month + 1, 1) - timedelta(seconds=1)
            result["date_from"] = start
            result["date_to"]   = end
            result["label"]     = f"tháng {month}/{year}"
            return result

    m = re.search(r"tháng\s*(\d{1,2})(?![/\d])", q)
    if m:
        month = int(m.group(1))
        year  = now.year
        if 1 <= month <= 12:
            start = datetime(year, month, 1)
            end   = datetime(year, 12, 31, 23, 59, 59) if month == 12 \
                    else datetime(year, month + 1, 1) - timedelta(seconds=1)
            result["date_from"] = start
            result["date_to"]   = end
            result["label"]     = f"tháng {month}/{year}"
            return result

    m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", q)
    if m:
        day, mth, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            target = datetime(yr, mth, day)
            result["date_from"] = target
            result["date_to"]   = target.replace(hour=23, minute=59, second=59)
            result["label"]     = f"ngày {day}/{mth}/{yr}"
            return result
        except ValueError:
            pass

    m = re.search(r"ngày\s*(\d{1,2})[/\-](\d{1,2})(?![/\-]\d)", q)
    if m:
        day, mth = int(m.group(1)), int(m.group(2))
        yr = now.year
        try:
            target = datetime(yr, mth, day)
            result["date_from"] = target
            result["date_to"]   = target.replace(hour=23, minute=59, second=59)
            result["label"]     = f"ngày {day}/{mth}/{yr}"
            return result
        except ValueError:
            pass

    return result


# ====================== CORE ======================

def retrieve(query: str, top_k: int = TOP_K):
    """
    Tìm kiếm vector trong Qdrant với tuỳ chọn filter / sort theo ngày.

    Tối ưu cho 50k+ vectors:
      - SearchParams(hnsw_ef=64) giảm tải so với mặc định 128.
      - Oversample chỉ khi cần re-sort phía client (sort_newest).
      - Date filter được đẩy xuống Qdrant → lọc trước khi search.
    """
    date_info = parse_date_filter(query)

    query_vector = embed_model.encode(
        "query: " + query,
        normalize_embeddings=True
    ).tolist()

    qdrant_filter = None
    if date_info["date_from"] or date_info["date_to"]:
        range_kwargs = {}
        if date_info["date_from"]:
            range_kwargs["gte"] = int(date_info["date_from"].timestamp())
        if date_info["date_to"]:
            range_kwargs["lte"] = int(date_info["date_to"].timestamp())

        qdrant_filter = Filter(
            must=[
                FieldCondition(
                    key="ngay_dang_ts",
                    range=Range(**range_kwargs)
                )
            ]
        )

    fetch_k       = top_k * OVERSAMPLE_FACTOR if date_info["sort_newest"] else top_k
    search_params = SearchParams(hnsw_ef=HNSW_EF, exact=False)

    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=qdrant_filter,
        limit=fetch_k,
        with_payload=True,
        search_params=search_params,
    ).points

    if date_info["sort_newest"]:
        results = sorted(
            results,
            key=lambda r: r.payload.get("ngay_dang_ts", 0),
            reverse=True
        )[:top_k]

    chunks = []
    for r in results:
        content_text = r.payload.get("content", "") or r.payload.get("tieu_de", "")

        ngay_str = r.payload.get("ngay_dang", "")
        if not ngay_str:
            ts = r.payload.get("ngay_dang_ts", -1)
            if ts and ts > 0:
                ngay_str = datetime.fromtimestamp(ts).strftime("%d/%m/%Y")

        chunks.append({
            "score":   round(r.score, 4),
            "tieu_de": r.payload.get("tieu_de", ""),
            "link":    r.payload.get("link", ""),
            "ngay":    ngay_str,
            "content": content_text[:MAX_CHARS],
        })

    return chunks, date_info


def build_prompt(query: str, chunks: list, date_info: dict) -> str:
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        date_tag = f"[📅 {chunk['ngay']}] " if chunk["ngay"] else ""
        context_parts.append(f"[Nguồn {i}] {date_tag}{chunk['content']}")

    context   = "\n\n---\n\n".join(context_parts)
    today_str = datetime.now().strftime("%d/%m/%Y")

    time_note = ""
    if date_info["label"]:
        time_note = (
            f"\n⚠️  Người dùng yêu cầu thông tin cho: {date_info['label']}. "
            "Hãy ưu tiên thông tin trong khoảng thời gian này."
        )

    return f"""Bạn là trợ lý thông tin của trường.
Ngày hiện tại: {today_str}{time_note}

Chỉ trả lời dựa trên dữ liệu dưới đây.
Nếu không tìm thấy thông tin phù hợp → nói: "Tôi không tìm thấy thông tin."
Nếu có nhiều thông tin từ nhiều thời điểm khác nhau, hãy ưu tiên thông tin MỚI NHẤT.

--- NGUỒN ---
{context}
--- HẾT NGUỒN ---

Câu hỏi: {query}
Trả lời:"""


def gemini_generate(prompt: str, max_retries: int = 3) -> str | None:
    """
    Gọi Gemini API với retry + exponential backoff.

    Free tier rate limit: ~10 RPM / 250 RPD.
    Khi bị 429 (quota vượt giới hạn), tự động chờ rồi thử lại.
    """
    generation_config = genai.types.GenerationConfig(
        max_output_tokens=MAX_TOKENS,
        temperature=0.2,   # thấp → trả lời sát nguồn hơn, ít sáng tạo
    )

    for attempt in range(max_retries + 1):
        try:
            response = gemini_model.generate_content(
                prompt,
                generation_config=generation_config,
            )
            return response.text.strip()

        except Exception as e:
            err_str = str(e).lower()

            # Rate limit (429) → chờ rồi thử lại
            if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                if attempt < max_retries:
                    wait = 2 ** (attempt + 2)   # 4s, 8s, 16s
                    print(f"⚠️  Rate limit, thử lại sau {wait}s... (lần {attempt + 1})")
                    time.sleep(wait)
                    continue
                else:
                    print("❌ Rate limit sau nhiều lần thử. Thử lại sau ít phút.")
                    return None

            # Lỗi kết nối
            if "connection" in err_str or "network" in err_str:
                print("❌ Không kết nối được Gemini API. Kiểm tra mạng.")
                return None

            # Bị block do safety filter
            if "finish_reason" in err_str or "safety" in err_str:
                print("⚠️  Nội dung bị chặn bởi safety filter của Gemini.")
                return None

            print(f"❌ Lỗi không xác định: {e}")
            return None

    return None


def _add_to_cache(key: str, value):
    """LRU cache giới hạn MAX_CACHE_SIZE entries."""
    if key in cache:
        cache.move_to_end(key)
    cache[key] = value
    if len(cache) > MAX_CACHE_SIZE:
        cache.popitem(last=False)


def ask(query: str) -> dict:
    if query in cache:
        print("⚡ Dùng cache")
        return cache[query]

    print(f"\n🔍 Truy vấn: {query}")
    print("   Đang tìm kiếm...")

    chunks, date_info = retrieve(query)

    if date_info["label"]:
        print(f"   🗓️  Bộ lọc ngày: {date_info['label']}")
    if date_info["sort_newest"]:
        print("   📅 Sắp xếp theo: mới nhất trước")

    if not chunks:
        suffix = f" cho {date_info['label']}" if date_info["label"] else ""
        return {"answer": f"Không tìm thấy thông tin{suffix}.", "sources": []}

    print(f"   Tìm thấy {len(chunks)} chunks")
    print("   Đang gọi Gemini API...")

    prompt = build_prompt(query, chunks, date_info)
    answer = gemini_generate(prompt)

    if not answer:
        return {"answer": "Lỗi khi gọi Gemini API.", "sources": []}

    result = {
        "answer": answer,
        "sources": [
            {
                "tieu_de": c["tieu_de"],
                "link":    c["link"],
                "score":   c["score"],
                "ngay":    c["ngay"],
            }
            for c in chunks
        ]
    }

    _add_to_cache(query, result)
    return result


def print_result(result: dict):
    print("\n" + "=" * 60)
    print("💬 TRẢ LỜI:")
    print("=" * 60)
    print(result["answer"])

    print("\n📎 Nguồn:")
    for i, src in enumerate(result["sources"], 1):
        date_tag = f"  [{src['ngay']}]" if src.get("ngay") else ""
        print(f"[{i}] {src['tieu_de']} (score: {src['score']}){date_tag}")
        print(f"    {src['link']}")

    print("=" * 60)


# ====================== MAIN ======================
if __name__ == "__main__":
    test_queries = [
        "Thông báo mới nhất của trường là gì?",
        "Làm cách nào để sinh viên từ khóa 50K về trước đăng kí học học kỳ I năm 2025-2026?",
        "Kế hoạch hoạt động đảm bảo chất lượng giáo dục năm học 2019-2020 được đăng vào ngày nào?",
        "Chương trình thạc sĩ ngành Kế toán có giấy chứng nhận kiểm định chất lượng theo thông tư nào?",
        "Liệt kê các chương trình bậc thạc sĩ đã có báo cáo tự đánh giá hoặc giấy chứng nhận kiểm định?",
        "Cung cấp link xem Kế hoạch công tác đảm bảo chất lượng năm học 2015-2016.",
        "Chuyên mục Đảm bảo chất lượng của Trường Đại học Kinh tế - Đại học Đà Nẵng bao gồm những mảng công tác chính nào?"
    ]

    for query in test_queries:
        result = ask(query)
        print_result(result)

    print("\n✅ Chế độ interactive (gõ 'exit' để thoát)\n")
    print("💡 Gợi ý: bạn có thể hỏi kèm thời gian, ví dụ:")
    print("   • 'thông báo mới nhất'")
    print("   • 'học bổng tháng trước'")
    print("   • 'lịch thi tuần này'")
    print("   • 'thông báo ngày 15/4/2025'\n")

    while True:
        query = input("❓ Câu hỏi: ").strip()
        if query.lower() in ("exit", "quit", "thoát"):
            break
        if not query:
            continue

        result = ask(query)
        print_result(result)