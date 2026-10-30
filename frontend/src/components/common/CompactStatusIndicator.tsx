import React from 'react';

interface CompactStatusIndicatorProps {
  message?: string;
  className?: string;
}

export const CompactStatusIndicator: React.FC<CompactStatusIndicatorProps> = ({
  message = 'Frontend preview · Live document analysis may not be enabled.',
  className = '',
}) => {
  return (
    <div
      role="status"
      className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono border border-slate-200/80 dark:border-white/10 bg-slate-100/70 dark:bg-slate-900/60 text-slate-600 dark:text-slate-400 backdrop-blur-md shadow-sm transition-all ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
      <span className="truncate">{message}</span>
    </div>
  );
};

export default CompactStatusIndicator;
