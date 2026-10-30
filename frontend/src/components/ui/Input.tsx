import React from 'react';
import { cn } from '../../lib/utils';

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', ...props }, ref) => {
    return (
      <input
        type={type}
        ref={ref}
        className={cn(
          'flex h-11 w-full rounded-xl border border-slate-700/80 bg-slate-900/60 px-4 py-2 text-sm text-slate-100 placeholder:text-slate-500 shadow-inner transition-colors duration-150',
          'focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/60',
          'disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';
