ChatBot_DUE 🤖
ChatBot_DUE là một hệ thống chatbot thông minh được phát triển nhằm hỗ trợ sinh viên và giảng viên tại Trường Đại học Kinh tế - Đại học Đà Nẵng (DUE). Dự án tích hợp các mô hình ngôn ngữ lớn (LLM) và khả năng xử lý dữ liệu để cung cấp thông tin chính xác và nhanh chóng.

🚀 Tính năng chính
Hỗ trợ đa mô hình: Tích hợp cả Google Gemini API và Ollama để linh hoạt trong việc xử lý ngôn ngữ.

Xử lý dữ liệu thông minh: Khả năng truy xuất và phân tích dữ liệu từ các tệp Excel và cơ sở dữ liệu SQL Server.

Kiến trúc hiện đại: Kết hợp giữa Backend Python (Flask) và Frontend React (TypeScript/Vite).

Triển khai dễ dàng: Hỗ trợ Docker để đóng gói và vận hành hệ thống một cách nhất quán trên nhiều môi trường.

🛠️ Công nghệ sử dụng
Backend
Ngôn ngữ: Python.

Framework: Flask.

AI/LLM: Gemini API, Ollama, PyTorch (đối với các tác vụ học máy chuyên sâu).

Database: SQL Server (sử dụng các tính năng nâng cao như Always Encrypted).

Frontend
Framework: React với TypeScript.

Build Tool: Vite.

Styling: CSS hiện đại, tối ưu cho trải nghiệm người dùng.

📂 Cấu trúc thư mục
Plaintext
ChatBot_DUE/
├── backend/            # Chứa mã nguồn Flask, logic AI và xử lý dữ liệu
│   ├── data/           # Các file dữ liệu (Excel, SQL)
│   └── query_gemini.py # Script xử lý tương tác với Gemini
├── frontend/           # Chứa mã nguồn React (Vite + TS)
├── docker-compose.yml  # Cấu hình triển khai Docker
└── README.md
⚙️ Cài đặt và Sử dụng
1. Cấu hình môi trường
Tạo file .env dựa trên file .env.example và điền các API Key cần thiết (như Gemini API Key).

Đảm bảo bạn không đẩy file .env thực tế lên GitHub để bảo mật thông tin.

2. Chạy dự án (Local)
Backend:

Bash
cd backend
pip install -r requirements.txt
python main.py
Frontend:

Bash
cd frontend
npm install
npm run dev
3. Triển khai với Docker
Bash
docker-compose up --build
