import hashlib
import textwrap
import pandas as pd
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from tqdm import tqdm

print("🔄 BẮT ĐẦU REBUILD VỚI CHUNKING + INCREMENTAL SAVE")

# ====================== 1. ĐỌC EXCEL ======================
df = pd.read_excel("data/Data_TongHop.xlsx", sheet_name="Sheet1")
df = df[['Mục', 'Tên chuyên mục', 'Tiêu đề', 'Link', 'Ngày đăng', 'nội dung']]
df['nội dung'] = df['nội dung'].astype(str).str.strip()
df = df.dropna(subset=['nội dung'])
df = df[df['nội dung'].str.len() > 100]

print(f"✅ Đã load {len(df)} dòng dữ liệu")

# ====================== 2. TẠO DOCUMENTS ======================
# FIX (style): removed leading whitespace from f-string using textwrap.dedent
# so Python indentation doesn't bleed into chunk text
documents = []
for _, row in df.iterrows():
    text = textwrap.dedent(f"""
        Mục: {row['Mục']}
        Chuyên mục: {row['Tên chuyên mục']}
        Tiêu đề: {row['Tiêu đề']}
        Ngày đăng: {row['Ngày đăng']}
        Link: {row['Link']}

        Nội dung chi tiết:
        {row['nội dung']}
    """).strip()

    doc = Document(
        text=text,
        metadata={
            "muc":        str(row['Mục']),
            "chuyen_muc": str(row['Tên chuyên mục']),
            "tieu_de":    str(row['Tiêu đề']),
            "link":       str(row['Link']),
            # FIX (style): cast all metadata values to str consistently
            "ngay_dang":  str(row['Ngày đăng']),
        }
    )
    documents.append(doc)

print(f"✅ Đã tạo {len(documents)} Documents")

# ====================== 3. CHUNKING ======================
print("✂️ Đang chunking documents...")
splitter = SentenceSplitter(
    chunk_size=512,
    chunk_overlap=80
)
nodes = splitter.get_nodes_from_documents(documents)
print(f"✅ Đã tạo {len(nodes)} chunks (từ {len(documents)} documents)")

# ====================== 4. KẾT NỐI QDRANT ======================
client = QdrantClient(host="localhost", port=6333)
collection_name = "due"

# FIX (bug): always recreate the collection to avoid duplicate vectors on re-run
if collection_name in [c.name for c in client.get_collections().collections]:
    client.delete_collection(collection_name)
    print(f"🗑️ Đã xoá collection cũ '{collection_name}'")

client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
)
print(f"✅ Đã tạo collection '{collection_name}'")

# ====================== 5. EMBEDDING TRỰC TIẾP VỚI SENTENCE-TRANSFORMERS ======================
# FIX (performance): use sentence-transformers directly instead of through LlamaIndex wrapper.
# The model is the same — we just cut out the abstraction layers and let the library
# batch everything in one optimised call.
#
# Use device="cuda" if you have a GPU — this alone gives a 10-20x speedup.
# Change to device="cpu" if not.
print("📦 Đang load model embedding...")
model = SentenceTransformer(
    "intfloat/multilingual-e5-large",
    device="cpu"   # ← change to "cuda" if GPU is available
)

# e5 models require a "query: " or "passage: " prefix.
# Chunks being indexed are passages.
texts = ["passage: " + node.get_content() for node in nodes]

print(f"🚀 Bắt đầu embedding {len(texts)} chunks...")
# FIX (performance): one large encode() call — batch_size=128 lets the model
# process efficiently internally; normalize_embeddings=True is required for e5 models.
embeddings = model.encode(
    texts,
    batch_size=128,          # FIX: was 30, larger batch = better throughput
    show_progress_bar=True,
    normalize_embeddings=True
)

# ====================== 6. LƯU VÀO QDRANT ======================
print("💾 Đang lưu vectors vào Qdrant...")

# FIX (bug): use deterministic IDs derived from chunk text hash.
# This means re-running the script produces the same IDs and upsert
# will overwrite rather than duplicate.
points = [
    PointStruct(
        id=int(hashlib.md5(texts[i].encode()).hexdigest()[:16], 16) % (2**63),
        vector=embeddings[i].tolist(),
        payload=nodes[i].metadata
        
    )
    for i in range(len(nodes))
]

# FIX (performance): upsert in large batches (256) directly — no LlamaIndex overhead
batch_size = 256
for i in tqdm(range(0, len(points), batch_size), desc="Saving to Qdrant"):
    client.upsert(
        collection_name=collection_name,
        points=points[i:i + batch_size]
    )

# ====================== 7. KIỂM TRA KẾT QUẢ ======================
info = client.get_collection(collection_name)
print("\n" + "=" * 70)
print("🎉 HOÀN THÀNH!")
print("=" * 70)
print(f"Collection          : {collection_name}")
print(f"Số vector đã lưu    : {info.points_count}")
print(f"Chunk size          : 512 tokens")
print(f"Batch size (embed)  : 128")
print(f"Batch size (upsert) : 256")
print(f"Model               : intfloat/multilingual-e5-large")
print("✅ Hoàn tất — không có duplicate, sẵn sàng query!")