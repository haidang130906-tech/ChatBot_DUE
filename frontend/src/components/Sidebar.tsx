import { Plus, MessageSquare, HelpCircle, Settings, History } from 'lucide-react';
import { motion } from 'motion/react';

const navItems = [
  { icon: MessageSquare, label: 'Chat', active: true },
  { icon: HelpCircle, label: 'Help' },
  { icon: Settings, label: 'Settings' },
];

export function Sidebar() {
  return (
    <aside className="hidden md:flex flex-col fixed left-0 top-0 h-full w-72 bg-surface-container-low border-r border-surface-container-high p-4 gap-4 z-40">
      <div className="flex items-center gap-3 px-3 py-6 mb-2">
        <div className="w-10 h-10 bg-surface-container-highest rounded-xl flex items-center justify-center border border-surface-container-highest">
          <span className="font-bold text-primary text-xl">D</span>
        </div>
        <div>
          <h1 className="text-xl font-extrabold text-primary leading-tight">DUE AI</h1>
          <p className="text-xs font-medium text-on-surface-variant/60 uppercase tracking-widest">Academic Partner</p>
        </div>
      </div>

      <motion.button
        whileHover={{ x: 4 }}
        whileTap={{ scale: 0.98 }}
        className="flex items-center justify-center gap-3 w-full bg-secondary-container text-white font-bold rounded-2xl px-4 py-4 shadow-lg shadow-secondary-container/20 transition-all"
      >
        <Plus className="w-5 h-5" strokeWidth={3} />
        <span className="text-base">New chat</span>
      </motion.button>

      <nav className="flex flex-col gap-1 mt-6 flex-grow">
        {navItems.map((item) => (
          <motion.a
            key={item.label}
            href="#"
            whileHover={{ x: 4 }}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl font-semibold transition-all duration-200 ${
              item.active 
                ? 'bg-secondary-container/10 text-secondary-container shadow-sm' 
                : 'text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            <item.icon className="w-5 h-5" />
            <span>{item.label}</span>
          </motion.a>
        ))}
      </nav>

      <div className="mt-auto border-t border-surface-container-high pt-4">
        <button className="w-full text-on-surface-variant flex items-center gap-3 px-4 py-3 hover:bg-surface-container-high rounded-xl transition-all">
          <History className="w-5 h-5" />
          <span className="font-semibold">Recent Activity</span>
        </button>
      </div>
    </aside>
  );
}
