import React from 'react';
import { cn } from '../../lib/utils';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  glow?: 'none' | 'indigo' | 'purple' | 'blue' | 'emerald';
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, glow = 'none', children, ...props }, ref) => {
    const glowClasses = {
      none: '',
      indigo: 'hover:shadow-indigo-500/10 hover:border-indigo-500/30',
      purple: 'hover:shadow-purple-500/10 hover:border-purple-500/30',
      blue: 'hover:shadow-blue-500/10 hover:border-blue-500/30',
      emerald: 'hover:shadow-emerald-500/10 hover:border-emerald-500/30',
    };

    return (
      <div
        ref={ref}
        className={cn(
          'glass-card rounded-2xl p-6 relative overflow-hidden',
          glowClasses[glow],
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';
