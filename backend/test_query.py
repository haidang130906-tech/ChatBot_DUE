from collections import OrderedDict
from datetime import datetime, timedelta
import re
import time

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, Range
import requests

# ====================== CONFIG ======================
QDRANT_HOST      = "localhost"
QDRANT_PORT      = 6333
COLLECTION_NAME  = "due"

EMBED_MODEL_NAME = "intfloat/multilingual-e5-large"

TOP_K            = 5      # tăng lên 5 để có nhiều nguồn hơn
MAX_CHARS        = 800    # tăng lên 800 để LLM có đủ thông tin

OLLAMA_URL       = "http://localhost:11434/api/generate"
OLLAMA_MODEL     = "llama3"

MAX_CACHE_SIZE   = 100

# ====================== INIT ======================
print("📦 Đang khởi tạo...")

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
        date_from   : datetime | None  — giới hạn dưới (gte)
        date_to     : datetime | None  — giới hạn trên (lte)
        sort_newest : bool             — True nếu cần sắp xếp mới → cũ
        label       : str              — mô tả ngắn để đưa vào prompt
    """
    now         = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    q           = query.lower()

    result = {"date_from": None, "date_to": None, "sort_newest": False, "label": ""}

    # ── mới nhất / gần đây ──────────────────────────────────────────────────
    if re.search(r"mới nhất|gần đây|mới cập nhật|cập nhật mới|tin mới", q):
        result["sort_newest"] = True
        result["label"] = "thông tin mới nhất"
        return result

    # ── hôm nay ─────────────────────────────────────────────────────────────
    if re.search(r"hôm nay|ngày hôm nay|ngày này", q):
        result["date_from"] = today_start
        result["date_to"]   = now
        result["label"]     = f"hôm nay ({today_start.strftime('%d/%m/%Y')})"
        return result

    # ── hôm qua ─────────────────────────────────────────────────────────────
    if re.search(r"hôm qua|ngày hôm qua|ngày qua", q):
        yesterday = today_start - timedelta(days=1)
        result["date_from"] = yesterday
        result["date_to"]   = today_start - timedelta(seconds=1)
        result["label"]     = f"hôm qua ({yesterday.strftime('%d/%m/%Y')})"
        return result

    # ── tuần này ────────────────────────────────────────────────────────────
    if re.search(r"tuần này|tuần hiện tại", q):
        start_of_week = today_start - timedelta(days=today_start.weekday())
        result["date_from"] = start_of_week
        result["date_to"]   = now
        result["label"]     = (
            f"tuần này ({start_of_week.strftime('%d/%m')} – {now.strftime('%d/%m/%Y')})"
        )
        return result

    # ── tuần trước ──────────────────────────────────────────────────────────
    if re.search(r"tuần trước|tuần vừa rồi|tuần vừa qua", q):
        start_of_week  = today_start - timedelta(days=today_start.weekday())
        end_last_week  = start_of_week - timedelta(seconds=1)
        start_last_week = start_of_week - timedelta(days=7)
        result["date_from"] = start_last_week
        result["date_to"]   = end_last_week
        result["label"]     = (
            f"tuần trước ({start_last_week.strftime('%d/%m')} – {end_last_week.strftime('%d/%m/%Y')})"
        )
        return result

    # ── X ngày qua ──────────────────────────────────────────────────────────
    m = re.search(r"(\d+)\s*ngày\s*(qua|gần đây|trước|vừa qua)", q)
    if m:
        n_days = int(m.group(1))
        result["date_from"] = today_start - timedelta(days=n_days)
        result["date_to"]   = now
        result["label"]     = f"{n_days} ngày gần đây"
        return result

    # ── tháng này ───────────────────────────────────────────────────────────
    if re.search(r"tháng này|tháng hiện tại", q):
        start_of_month = today_start.replace(day=1)
        result["date_from"] = start_of_month
        result["date_to"]   = now
        result["label"]     = f"tháng này (tháng {now.month}/{now.year})"
        return result

    # ── tháng trước ─────────────────────────────────────────────────────────
    if re.search(r"tháng trước|tháng vừa rồi|tháng vừa qua", q):
        if now.month == 1:
            lm_year, lm_month = now.year - 1, 12
        else:
            lm_year, lm_month = now.year, now.month - 1
        start_last_month   = datetime(lm_year, lm_month, 1)
        start_this_month   = today_start.replace(day=1)
        result["date_from"] = start_last_month
        result["date_to"]   = start_this_month - timedelta(seconds=1)
        result["label"]     = f"tháng trước (tháng {lm_month}/{lm_year})"
        return result

    # ── X tháng qua ─────────────────────────────────────────────────────────
    m = re.search(r"(\d+)\s*tháng\s*(qua|gần đây|trước|vừa qua)", q)
    if m:
        n_months = int(m.group(1))
        result["date_from"] = today_start - timedelta(days=n_months * 30)
        result["date_to"]   = now
        result["label"]     = f"{n_months} tháng gần đây"
        return result

    # ── năm ngoái / năm trước ───────────────────────────────────────────────
    if re.search(r"năm ngoái|năm trước", q):
        last_year = now.year - 1
        result["date_from"] = datetime(last_year, 1, 1)
        result["date_to"]   = datetime(last_year, 12, 31, 23, 59, 59)
        result["label"]     = f"năm {last_year}"
        return result

    # ── năm nay ─────────────────────────────────────────────────────────────
    if re.search(r"năm nay|năm hiện tại", q):
        result["date_from"] = datetime(now.year, 1, 1)
        result["date_to"]   = now
        result["label"]     = f"năm {now.year}"
        return result

    # ── tháng X/YYYY hoặc tháng X năm YYYY ─────────────────────────────────
    m = re.search(r"tháng\s*(\d{1,2})[/\s\-]+(\d{4})", q)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year, 12, 31, 23, 59, 59)
            else:
                end = datetime(year, month + 1, 1) - timedelta(seconds=1)
            result["date_from"] = start
            result["date_to"]   = end
            result["label"]     = f"tháng {month}/{year}"
            return result

    # ── tháng X (không có năm → dùng năm hiện tại) ─────────────────────────
    m = re.search(r"tháng\s*(\d{1,2})(?![/\d])", q)
    if m:
        month = int(m.group(1))
        year  = now.year
        if 1 <= month <= 12:
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year, 12, 31, 23, 59, 59)
            else:
                end = datetime(year, month + 1, 1) - timedelta(seconds=1)
            result["date_from"] = start
            result["date_to"]   = end
            result["label"]     = f"tháng {month}/{year}"
            return result

    # ── ngày DD/MM/YYYY, DD-MM-YYYY, hoặc ngày DD/MM ───────────────────────
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

    return result  # → không có điều kiện ngày


# ====================== CORE ======================

def retrieve(query: str, top_k: int = TOP_K):
    """
    Tìm kiếm vector trong Qdrant với tuỳ chọn filter / sort theo ngày.

    - Nếu query có điều kiện ngày: áp Qdrant Filter trên ngay_dang_ts.
    - Nếu "mới nhất": lấy top_k * 3 kết quả rồi re-sort client-side.
    - Trả (chunks, date_info).
    """
    date_info = parse_date_filter(query)

    # encode query với prefix "query: " và normalize để khớp với lúc index
    query_vector = embed_model.encode(
        "query: " + query,
        normalize_embeddings=True
    ).tolist()

    # Xây dựng Qdrant filter nếu có khoảng ngày
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

    # Với "mới nhất" → lấy nhiều hơn rồi re-sort theo ngày
    fetch_k = top_k * 3 if date_info["sort_newest"] else top_k

    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=qdrant_filter,
        limit=fetch_k,
        with_payload=True
    ).points

    # Re-sort theo ngày mới nhất (client-side) nếu cần
    if date_info["sort_newest"]:
        results = sorted(
            results,
            key=lambda r: r.payload.get("ngay_dang_ts", 0),
            reverse=True
        )[:top_k]

    chunks = []
    for r in results:
        content_text = r.payload.get("content", "") or r.payload.get("tieu_de", "")

        # Lấy chuỗi ngày để hiển thị
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
    """
    Xây dựng prompt đầy đủ cho LLM:
      - Role + ngày hiện tại
      - Ghi chú về khoảng thời gian người dùng yêu cầu (nếu có)
      - Context từ các chunks (kèm ngày đăng)
      - Câu hỏi
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        date_tag = f"[📅 {chunk['ngay']}] " if chunk["ngay"] else ""
        context_parts.append(f"[Nguồn {i}] {date_tag}{chunk['content']}")

    context = "\n\n---\n\n".join(context_parts)

    today_str = datetime.now().strftime("%d/%m/%Y")

    # Thêm ghi chú thời gian vào prompt nếu người dùng hỏi theo khoảng ngày
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


def local_generate(prompt: str, max_retries: int = 2):
    """Gọi Ollama local với retry + timeout hợp lý."""
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=60
            )

            if response.status_code != 200:
                print(f"❌ Lỗi Ollama (HTTP {response.status_code}): {response.text}")
                return None

            try:
                data = response.json()
            except ValueError as json_err:
                print(f"❌ Ollama trả về non-JSON: {json_err}")
                return None

            return data.get("response", "").strip()

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"⚠️  Timeout lần {attempt + 1}, thử lại sau {wait}s...")
                time.sleep(wait)
            else:
                print("❌ Timeout sau nhiều lần thử.")
                return None

        except requests.exceptions.ConnectionError:
            print("❌ Không kết nối được Ollama. Hãy đảm bảo Ollama đang chạy.")
            return None

        except Exception as e:
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
    print("   Đang gọi LLM local...")

    prompt = build_prompt(query, chunks, date_info)
    answer = local_generate(prompt)

    if not answer:
        return {"answer": "Lỗi khi gọi local model.", "sources": []}

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
        "Làm cách nào để sinh viên từ khóa 50K về trước đăng kí học học kỳ I năm 2025-2026?"
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