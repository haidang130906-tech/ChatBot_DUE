import { Mic, SendHorizonal } from 'lucide-react';
import { motion } from 'motion/react';

export function ChatInput() {
  return (
    <div className="w-full max-w-4xl px-4">
      <div className="relative group">
        <div className="absolute inset-0 bg-primary/5 rounded-[2.5rem] blur-xl opacity-0 group-focus-within:opacity-100 transition-opacity duration-500"></div>
        <div className="relative flex items-center bg-surface-container-high rounded-[2.5rem] p-2 pr-4 shadow-sm border border-surface-container-highest focus-within:border-primary/20 focus-within:bg-surface-container-lowest transition-all duration-300">
          <input 
            className="w-full bg-transparent border-none focus:ring-0 px-6 py-4 text-on-surface placeholder:text-on-surface-variant/50 font-medium"
            placeholder="Ask Gemini at DUE..."
            type="text"
          />
          <div className="flex items-center gap-2">
            <button className="w-11 h-11 flex items-center justify-center rounded-full hover:bg-surface-container-highest transition-colors text-on-surface-variant">
              <Mic className="w-5 h-5" />
            </button>
            <motion.button 
              whileTap={{ scale: 0.9 }}
              className="w-11 h-11 flex items-center justify-center rounded-full bg-primary text-white hover:bg-primary/90 transition-colors shadow-lg"
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
