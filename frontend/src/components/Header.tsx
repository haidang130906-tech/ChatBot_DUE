import { Search, Menu } from 'lucide-react';
import { motion } from 'motion/react';

export function Header() {
  return (
    <header className="flex justify-between items-center px-6 md:px-8 w-full sticky top-0 z-50 bg-surface/80 backdrop-blur-md h-16 border-b border-surface-container-high/50">
      <div className="flex items-center gap-4">
        <button className="md:hidden p-2 hover:bg-surface-container-high rounded-full transition-colors">
          <Menu className="w-6 h-6 text-on-surface-variant" />
        </button>
        <span className="text-2xl font-extrabold text-primary tracking-tight">DUE</span>
      </div>
      
      <div className="flex items-center gap-4">
        <motion.button 
          whileTap={{ scale: 0.95 }}
          className="p-2 hover:bg-surface-container-high transition-all duration-200 rounded-full"
        >
          <Search className="w-5 h-5 text-on-surface-variant" />
        </motion.button>
        
        <motion.div 
          whileTap={{ scale: 0.95 }}
          className="w-9 h-9 rounded-full overflow-hidden border border-surface-container-highest cursor-pointer shadow-sm"
        >
          <img 
            alt="User Profile" 
            className="w-full h-full object-cover"
            src="https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&q=80&w=100"
          />
        </motion.div>
      </div>
    </header>
  );
}
