from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# Import hàm ask từ 2 file xử lý RAG của team
import test_api
import test_query

# ====================== KHỞI TẠO APP ======================
app = FastAPI(
    title="API Chatbot DUE",
    description="Backend API kết nối Frontend với hệ thống RAG của Đại học Kinh tế Đà Nẵng",
    version="1.0.0"
)

# ====================== CẤU HÌNH CORS ======================
# Cho phép Frontend (React/Vite) ở các port khác gọi API mà không bị chặn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Trong môi trường production, hãy thay "*" bằng URL frontend thật
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================== ĐỊNH NGHĨA DỮ LIỆU (PYDANTIC) ======================
# 1. Định nghĩa dữ liệu Frontend gửi lên
class ChatRequest(BaseModel):
    message: str
    use_local: Optional[bool] = False  # Gửi True nếu muốn dùng Ollama (test_query)

# 2. Định nghĩa dữ liệu Backend trả về (Để API có cấu trúc rõ ràng)
class SourceItem(BaseModel):
    tieu_de: str
    link: str
    score: float
    ngay: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem]

# ====================== CÁC ENDPOINT (API ROUTES) ======================

@app.get("/")
async def root():
    """Trang chủ để test xem Server API có đang chạy không"""
    return {"message": "Chào mừng đến với API Chatbot DUE! Hệ thống RAG đang hoạt động."}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint chính xử lý tin nhắn của người dùng.
    """
    user_message = request.message.strip()
    
    # Kiểm tra tin nhắn rỗng
    if not user_message:
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống")

    try:
        # Nếu Frontend gửi use_local = True -> Chạy Ollama
        if request.use_local:
            print(f"🤖 Đang dùng mô hình LOCAL (Ollama) cho câu hỏi: {user_message}")
            result = test_query.ask(user_message)
        
        # Mặc định -> Chạy Gemini API
        else:
            print(f"☁️ Đang dùng mô hình CLOUD (Gemini) cho câu hỏi: {user_message}")
            result = test_api.ask(user_message)
            
        return result # Trả về dictionary trực tiếp, FastAPI sẽ tự chuyển thành JSON
        
    except Exception as e:
        print(f"❌ Lỗi server: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")

# ====================== CHẠY SERVER ======================
if __name__ == "__main__":
    # Chạy server ở port 8000, host 0.0.0.0 để có thể truy cập từ Docker hoặc LAN
    print("🚀 Bắt đầu khởi động Server FastAPI...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)