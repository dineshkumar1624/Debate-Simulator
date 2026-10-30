import React from 'react';
import { cn } from '../../lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'pro' | 'con' | 'judge' | 'evidence' | 'synthesis' | 'outline';
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'default',
  children,
  ...props
}) => {
  const variants = {
    default: 'bg-slate-100 text-slate-700 border-slate-200/80 dark:bg-slate-800/80 dark:text-slate-300 dark:border-slate-700/60',
    pro: 'bg-sky-50 text-sky-700 border-sky-200/90 dark:bg-blue-500/15 dark:text-blue-400 dark:border-blue-500/30 font-semibold',
    con: 'bg-pink-50 text-pink-700 border-pink-200/90 dark:bg-pink-500/15 dark:text-pink-400 dark:border-pink-500/30 font-semibold',
    judge: 'bg-purple-50 text-purple-700 border-purple-200/90 dark:bg-purple-500/15 dark:text-purple-400 dark:border-purple-500/30 font-semibold',
    evidence: 'bg-emerald-50 text-emerald-700 border-emerald-200/90 dark:bg-emerald-500/15 dark:text-emerald-400 dark:border-emerald-500/30 font-semibold',
    synthesis: 'bg-amber-50 text-amber-700 border-amber-200/90 dark:bg-amber-500/15 dark:text-amber-400 dark:border-amber-500/30 font-semibold',
    outline: 'bg-white/80 text-slate-700 border-slate-200 dark:bg-transparent dark:text-slate-400 dark:border-slate-700/80',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border tracking-wide uppercase',
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
};
