import React from 'react';
import { HelpCircle, MessagesSquare, CheckCircle2, Scale, Sparkles } from 'lucide-react';

export const HowItWorks: React.FC = () => {
  const steps = [
    {
      step: '01',
      action: 'ASK',
      title: 'Enter your question.',
      description: 'Formulate any complex policy, philosophical, or technological proposition to be scrutinized.',
      icon: HelpCircle,
      accent: 'border-sky-200 dark:border-sky-500/30 text-sky-600 dark:text-sky-400 bg-sky-50 dark:bg-sky-950/40',
      badgeColor: 'text-sky-700 dark:text-sky-300 bg-sky-50 dark:bg-sky-950/40 border-sky-200 dark:border-sky-500/30',
    },
    {
      step: '02',
      action: 'DEBATE',
      title: 'Two AI agents build opposing perspectives.',
      description: 'Agent Alpha and Agent Beta construct rigorous affirmative and negative cases across rounds.',
      icon: MessagesSquare,
      accent: 'border-blue-200 dark:border-blue-500/30 text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40',
      badgeColor: 'text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-500/30',
    },
    {
      step: '03',
      action: 'VERIFY',
      title: 'Important claims are checked against evidence.',
      description: 'Factual assertions are isolated and verified against retrieved external citation datasets.',
      icon: CheckCircle2,
      accent: 'border-emerald-200 dark:border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40',
      badgeColor: 'text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-500/30',
    },
    {
      step: '04',
      action: 'EVALUATE',
      title: 'An independent AI judge evaluates both sides.',
      description: 'A third-party judge evaluates reasoning validity, fallacies, and counterargument strength.',
      icon: Scale,
      accent: 'border-purple-200 dark:border-purple-500/30 text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/40',
      badgeColor: 'text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-950/40 border-purple-200 dark:border-purple-500/30',
    },
    {
      step: '05',
      action: 'SYNTHESIZE',
      title: 'The system generates a balanced response.',
      description: 'Produces a nuanced synthesis outlining consensus, key tensions, and confidence levels.',
      icon: Sparkles,
      accent: 'border-amber-200 dark:border-amber-500/30 text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40',
      badgeColor: 'text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-500/30',
    },
  ];

  return (
    <section id="how-it-works" className="py-20 relative bg-white/70 dark:bg-transparent border-y border-slate-200/50 dark:border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-indigo-200/80 dark:border-indigo-500/30 bg-indigo-50/90 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
            Structured Cognitive Flow
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#0F172A] dark:text-white tracking-tight">
            FROM QUESTION TO EVIDENCE-GROUNDED ANSWER
          </h2>
          <p className="text-slate-600 dark:text-slate-300 text-sm sm:text-base leading-relaxed">
            A 5-stage dialectical sequence that moves beyond one-shot prompts into structured, evidence-verified reasoning.
          </p>
        </div>

        {/* Timeline Container */}
        <div className="relative">
          {/* Horizontal connecting flow line for desktop */}
          <div className="hidden lg:block absolute top-[52px] left-12 right-12 h-[2px] bg-gradient-to-r from-sky-300 via-purple-300 to-amber-300 z-0 opacity-70">
            <div className="w-full h-full bg-gradient-to-r from-transparent via-white dark:via-slate-800 to-transparent animate-pulse" />
          </div>

          {/* Cards Grid: horizontal on desktop, vertical on mobile */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-5 relative z-10">
            {steps.map((item, index) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.step}
                  className="glass-card rounded-2xl p-5 border border-slate-200/90 dark:border-white/10 flex flex-col justify-between group hover:border-indigo-300 dark:hover:border-indigo-500/40 relative bg-white/95 dark:bg-[#080d1e]/85 shadow-sm hover:shadow-md transition-all duration-300 backdrop-blur-md"
                >
                  <div>
                    {/* Top Row: Number badge and icon */}
                    <div className="flex items-center justify-between mb-4">
                      <span className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded-lg border ${item.badgeColor}`}>
                        {item.step} — {item.action}
                      </span>
                      <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${item.accent} transition-transform group-hover:scale-110 duration-200 shadow-sm`}>
                        <Icon className="w-4 h-4" />
                      </div>
                    </div>

                    {/* Step Title & Description */}
                    <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white mb-2 tracking-tight group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                      {item.title}
                    </h3>
                    <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed font-normal">
                      {item.description}
                    </p>
                  </div>

                  {/* Flow arrow indicator */}
                  {index < steps.length - 1 && (
                    <div className="hidden lg:flex absolute -right-3 top-[44px] z-20 w-6 h-6 rounded-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 items-center justify-center text-slate-400 text-xs shadow-sm">
                      →
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
