import { Mic, SendHorizonal } from 'lucide-react';
import { motion } from 'motion/react';
import { useState, KeyboardEvent } from 'react';

// Khai báo các thuộc tính mà ChatInput sẽ nhận
interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSendMessage, disabled }: ChatInputProps) {
  const [text, setText] = useState("");

  // Hàm xử lý gửi tin nhắn
  const handleSend = () => {
    if (text.trim() && !disabled) {
      onSendMessage(text);
      setText(""); // Xóa trắng ô nhập sau khi gửi
    }
  };

  // Gửi tin nhắn khi nhấn phím Enter
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div className="w-full max-w-4xl px-4">
      <div className="relative group">
        <div className="absolute inset-0 bg-primary/5 rounded-[2.5rem] blur-xl opacity-0 group-focus-within:opacity-100 transition-opacity duration-500"></div>
        <div className="relative flex items-center bg-surface-container-high rounded-[2.5rem] p-2 pr-4 shadow-sm border border-surface-container-highest focus-within:border-primary/20 focus-within:bg-surface-container-lowest transition-all duration-300">
          <input 
            className="w-full bg-transparent border-none focus:ring-0 px-6 py-4 text-on-surface placeholder:text-on-surface-variant/50 font-medium disabled:opacity-50"
            placeholder="Ask Gemini at DUE..."
            type="text"
            value={text} // Kết nối với state
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled} // Vô hiệu hóa khi đang xử lý
          />
          <div className="flex items-center gap-2">
            <button 
              disabled={disabled}
              className="w-11 h-11 flex items-center justify-center rounded-full hover:bg-surface-container-highest transition-colors text-on-surface-variant disabled:opacity-30"
            >
              <Mic className="w-5 h-5" />
            </button>
            <motion.button 
              whileTap={{ scale: 0.9 }}
              onClick={handleSend} // Kích hoạt hàm gửi[cite: 3]
              disabled={disabled || !text.trim()} // Chặn gửi khi trống hoặc đang tải
              className="w-11 h-11 flex items-center justify-center rounded-full bg-primary text-white hover:bg-primary/90 transition-colors shadow-lg disabled:bg-gray-400 disabled:shadow-none"
            >
              <SendHorizonal className="w-5 h-5" />
            </motion.button>
          </div>
        </div>
      </div>
      <p className="text-center text-[11px] font-medium text-on-surface-variant/40 mt-4 leading-relaxed">
        Gemini may display inaccurate info, including about people, so double-check its responses. 
        <a className="underline ml-1 hover:text-on-surface-variant transition-colors" href="#">Your privacy & DUE AI</a>
      </p>
    </div>
  );
}