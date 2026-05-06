import { motion } from 'motion/react';
import { GraduationCap, Calendar, FileText, MessageSquare, History, Settings } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { SuggestionCard } from './components/SuggestionCard';
import { ChatInput } from './components/ChatInput';

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
              transition={{ duration: 0.6, ease: "easeOut" }}
              className="mb-8 w-20 h-20 rounded-3xl bg-surface-container-high border border-surface-container-highest flex items-center justify-center p-4 shadow-sm"
            >
              <span className="text-3xl font-extrabold text-primary">DUE</span>
            </motion.div>
            
            <motion.h2 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="text-4xl md:text-5xl font-bold text-primary mb-6 tracking-tight max-w-3xl"
            >
              Hello, <span className="text-secondary">Alex</span>. How can I help you today with your DUE studies?
            </motion.h2>
            
            <motion.p 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="text-lg md:text-xl text-on-surface-variant max-w-2xl font-medium opacity-80"
            >
              I'm Gemini, your AI partner at DUE. Start your study day or research project here.
            </motion.p>
          </section>

          {/* Suggestions Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full mb-12">
            {suggestions.map((item, idx) => (
              <SuggestionCard key={item.title} {...item} index={idx} />
            ))}
          </div>

          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="text-xs font-semibold text-on-surface-variant/50 uppercase tracking-widest mb-12"
          >
            Based on your DUE account activity.
          </motion.p>

          {/* Chat Input Section */}
          <div className="w-full flex flex-col items-center mt-auto pb-8">
            <ChatInput />
          </div>
        </main>
      </div>

      {/* Mobile Bottom Nav */}
      <nav className="md:hidden fixed bottom-0 left-0 w-full bg-surface-container-high border-t border-surface-container-highest flex justify-around py-3 px-4 z-50">
        <button className="flex flex-col items-center gap-1 text-primary">
          <MessageSquare className="w-6 h-6" />
          <span className="text-[10px] font-bold">Chat</span>
        </button>
        <button className="flex flex-col items-center gap-1 text-on-surface-variant/60">
          <History className="w-6 h-6" />
          <span className="text-[10px] font-bold">Activity</span>
        </button>
        <button className="flex flex-col items-center gap-1 text-on-surface-variant/60">
          <Settings className="w-6 h-6" />
          <span className="text-[10px] font-bold">Settings</span>
        </button>
      </nav>
    </div>
  );
}

