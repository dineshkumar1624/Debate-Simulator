import React from 'react';
import { cn } from '../../lib/utils';

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          'flex min-h-[100px] w-full rounded-xl border border-slate-700/80 bg-slate-900/60 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 shadow-inner transition-colors duration-150 resize-y',
          'focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/60',
          'disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        {...props}
      />
    );
  }
);

Textarea.displayName = 'Textarea';
