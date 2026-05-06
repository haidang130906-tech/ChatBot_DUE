import { motion } from 'motion/react';
import { LucideIcon } from 'lucide-react';

interface SuggestionCardProps {
  icon: LucideIcon;
  iconBg: string;
  iconColor: string;
  title: string;
  description: string;
  index: number;
}

export function SuggestionCard({ icon: Icon, iconBg, iconColor, title, description, index }: SuggestionCardProps) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 * index, duration: 0.5, ease: "easeOut" }}
      whileHover={{ y: -4 }}
      className="suggestion-card-shadow group relative flex flex-col items-start bg-surface-container-lowest p-8 rounded-3xl text-left border border-transparent hover:border-surface-container-highest transition-all duration-300"
    >
      <div 
        className="w-12 h-12 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300"
        style={{ backgroundColor: iconBg }}
      >
        <Icon className="w-6 h-6" style={{ color: iconColor }} />
      </div>
      <h3 className="text-xl font-bold text-primary mb-2 leading-tight">
        {title}
      </h3>
      <p className="text-on-surface-variant text-sm leading-relaxed opacity-80">
        {description}
      </p>
    </motion.button>
  );
}
