import textwrap
from datetime import datetime

import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.http.models import ScrollRequest
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import aiohttp


print("🔄 ĐANG UPDATE PAYLOAD (thêm content) - KHÔNG RE-EMBEDDING")

# ====================== 1. KẾT NỐI QDRANT ======================
client = QdrantClient(host="localhost", port=6333)
collection_name = "due"

existing = [c.name for c in client.get_collections().collections]
if collection_name not in existing:
    raise RuntimeError(f"Collection '{collection_name}' không tồn tại.")

info = client.get_collection(collection_name)
total_points = info.points_count
print(f"✅ Collection '{collection_name}' có {total_points:,} points")

# ====================== 2. SCROLL TẤT CẢ POINTS TỪ QDRANT ======================
# Read real IDs + existing payload directly from Qdrant.
# with_vectors=False — we never load vectors, keeping memory low.
print("📜 Đang scroll tất cả points từ Qdrant...")

all_points = []
offset = None
batch_size = 256

with tqdm(total=total_points, desc="Scrolling") as pbar:
    while True:
        result, next_offset = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,   # need existing payload to build updated one
            with_vectors=False,  # never load vectors — saves memory & time
        )
        all_points.extend(result)
        pbar.update(len(result))

        if next_offset is None:
            break
        offset = next_offset

print(f"✅ Đã scroll {len(all_points):,} points")

# ====================== 3. ĐỌC EXCEL ĐỂ LẤY NỘI DUNG ======================
df = pd.read_excel("Data_TongHop.xlsx", sheet_name="Sheet1")
df = df[['Tiêu đề', 'Link', 'Ngày đăng', 'nội dung']]
df['nội dung'] = df['nội dung'].astype(str).str.strip()
df = df.dropna(subset=['nội dung'])
df = df[df['nội dung'].str.len() > 100]

# Build lookup: link → nội dung (link is unique per article)
link_to_content = dict(zip(df['Link'].astype(str), df['nội dung']))
link_to_ngay    = dict(zip(df['Link'].astype(str), df['Ngày đăng']))
print(f"✅ Đã load {len(link_to_content):,} bài từ Excel")

# ====================== 4. BUILD UPDATE PAIRS ======================
# Match each Qdrant point back to its source article via the `link` field
# in the existing payload, then attach the full content.
print("🔨 Đang map points → content...")

id_payload_pairs = []
skipped = 0

for point in tqdm(all_points, desc="Mapping"):
    existing_payload = point.payload or {}
    link = existing_payload.get("link", "")
    content = link_to_content.get(link)

    if not content:
        skipped += 1
        continue

    # Parse timestamp
    try:
        ngay_dang_ts = int(
            datetime.strptime(str(link_to_ngay.get(link, "")).strip(), "%d/%m/%Y").timestamp()
        )
    except Exception:
        ngay_dang_ts = 0

    id_payload_pairs.append((point.id, {
        "content":      content,
        "ngay_dang_ts": ngay_dang_ts,
    }))

print(f"✅ Mapped: {len(id_payload_pairs):,} | Skipped (no match): {skipped:,}")

# ====================== 5. BATCH UPDATE ======================
async def update_one(session: aiohttp.ClientSession, point_id: int, payload: dict):
    url = f"http://localhost:6333/collections/{collection_name}/points/payload"
    body = {
        "payload": payload,
        "points": [point_id]
    }
    async with session.post(url, json=body) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise Exception(f"HTTP {resp.status}: {text}")

async def run_updates(pairs: list, max_concurrent: int = 16):
    # One shared TCP connector — reuses connections, no port exhaustion
    connector = aiohttp.TCPConnector(
        limit=max_concurrent,
        keepalive_timeout=30,
        enable_cleanup_closed=True
    )
    timeout = aiohttp.ClientTimeout(total=30)

    failed = 0
    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_update(session, pair):
        nonlocal failed
        point_id, payload = pair
        async with semaphore:
            try:
                await update_one(session, point_id, payload)
            except Exception as e:
                nonlocal failed
                failed += 1
                print(f"\n⚠️  Lỗi tại point {point_id}: {e}")

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout
    ) as session:
        tasks = [bounded_update(session, pair) for pair in pairs]

        # Process with progress bar in chunks to avoid creating 130k tasks at once
        chunk_size = 1000
        with tqdm(total=len(tasks), desc="Updating") as pbar:
            for i in range(0, len(tasks), chunk_size):
                chunk = tasks[i:i + chunk_size]
                await asyncio.gather(*chunk)
                pbar.update(len(chunk))

    return failed

print(f"💾 Đang update payload (async, connection pooling)...")
failed = asyncio.run(run_updates(id_payload_pairs, max_concurrent=16))


# ====================== 6. KẾT QUẢ ======================
info = client.get_collection(collection_name)
print("\n" + "=" * 70)
print("🎉 HOÀN THÀNH UPDATE PAYLOAD!")
print("=" * 70)
print(f"Collection       : {collection_name}")
print(f"Tổng vectors     : {info.points_count:,}")
print(f"Đã update        : {len(id_payload_pairs) - failed:,}")
print(f"Thất bại         : {failed:,}")
print(f"Skipped          : {skipped:,}")
print("✅ Vectors không bị thay đổi — chỉ payload được cập nhật!")