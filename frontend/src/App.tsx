import { motion } from 'framer-motion'; // Kiểm tra lại nếu team dùng 'motion/react' thì đổi lại nhé
import { GraduationCap, Calendar, FileText, MessageSquare, History, Settings } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { SuggestionCard } from './components/SuggestionCard';
import { ChatInput } from './components/ChatInput';
import { useState } from 'react';

const suggestions = [
  {
    icon: GraduationCap,
    iconBg: '#78fc9c',
    iconColor: '#005225',
    title: 'Thông tin tuyển sinh',
    description: 'Tìm hiểu về chỉ tiêu, phương thức xét tuyển và các ngành đào tạo của nhà trường năm 2024.'
  },
  {
    icon: Calendar,
    iconBg: '#ffdbce',
    iconColor: '#7f2b00',
    title: 'Lịch học & Thời khóa biểu',
    description: 'Tra cứu lịch học, lịch thi và các mốc thời gian quan trọng trong học kỳ này.'
  },
  {
    icon: FileText,
    iconBg: '#d6e3ff',
    iconColor: '#2d476f',
    title: 'Thủ tục hành chính',
    description: 'Hướng dẫn các quy trình xin cấp bảng điểm, xác nhận sinh viên và các giấy tờ liên quan.'
  }
];

export default function App() {
  // --- PHẦN 1: LOGIC XỬ LÝ ---
  const [chatHistory, setChatHistory] = useState<{role: string, text: string}[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return;

    setChatHistory(prev => [...prev, { role: "user", text: message }]);
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message, use_local: false }),
      });

      if (!response.ok) throw new Error("Lỗi kết nối");
      const data = await response.json();
      setChatHistory(prev => [...prev, { role: "bot", text: data.answer }]);
    } catch (error) {
      setChatHistory(prev => [...prev, { role: "bot", text: "Lỗi kết nối server!" }]);
    } finally {
      setIsLoading(false);
    }
  };

  // --- PHẦN 2: GIAO DIỆN (JSX) ---
  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      
      <div className="flex-grow md:ml-72 flex flex-col items-center">
        <Header />
        
        <main className="w-full max-w-6xl mx-auto flex flex-col items-center justify-center flex-grow p-6 md:p-12">
          {/* Hero Section */}
          <section className="w-full flex flex-col items-center text-center mb-16">
            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="mb-8 w-20 h-20 rounded-3xl bg-surface-container-high border flex items-center justify-center p-4"
            >
              <span className="text-3xl font-extrabold text-primary">DUE</span>
            </motion.div>
            
            <h2 className="text-4xl md:text-5xl font-bold text-primary mb-6">
              Hello, <span className="text-secondary">Alex</span>.
            </h2>
          </section>

          {/* Chat History */}
          <div className="w-full max-w-3xl mb-8 space-y-4 overflow-y-auto max-h-[400px]">
            {chatHistory.map((chat, index) => (
              <div key={index} className={`flex ${chat.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`p-4 rounded-2xl ${chat.role === 'user' ? 'bg-primary text-white' : 'bg-gray-200'}`}>
                  {chat.text}
                </div>
              </div>
            ))}
            {isLoading && <div className="text-sm animate-pulse">Đang trả lời...</div>}
          </div>

          {/* Suggestions Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full mb-12">
            {suggestions.map((item, idx) => (
              <SuggestionCard key={item.title} {...item} index={idx} />
            ))}
          </div>

          {/* Input Section */}
          <div className="w-full flex flex-col items-center mt-auto pb-8">
            <ChatInput onSendMessage={handleSendMessage} disabled={isLoading} />
          </div>
        </main>
      </div>
    </div>
  );
}