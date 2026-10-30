import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Sparkles } from 'lucide-react';
import { Button } from '../ui/Button';

export const FinalCTA: React.FC = () => {
  return (
    <section className="py-24 relative overflow-hidden">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Main CTA Card with soft indigo/lavender gradient background */}
        <div className="relative rounded-3xl overflow-hidden glass-panel border border-indigo-200/80 dark:border-white/10 p-8 sm:p-16 text-center shadow-[0_20px_60px_-15px_rgba(79,70,229,0.12)] dark:shadow-[0_20px_60px_-15px_rgba(0,0,0,0.5)] bg-gradient-to-b from-indigo-50/90 via-purple-50/60 to-white dark:from-[#0f1738]/90 dark:via-[#161230]/70 dark:to-[#080d1e]">
          {/* Subtle neural network background SVG */}
          <div className="absolute inset-0 pointer-events-none opacity-25 dark:opacity-40">
            <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
              <line x1="20%" y1="30%" x2="50%" y2="50%" stroke="#6366f1" strokeWidth="1" strokeDasharray="3 3" />
              <line x1="80%" y1="30%" x2="50%" y2="50%" stroke="#ec4899" strokeWidth="1" strokeDasharray="3 3" />
              <line x1="50%" y1="50%" x2="50%" y2="80%" stroke="#a855f7" strokeWidth="1" strokeDasharray="3 3" />
              <circle cx="20%" cy="30%" r="4" fill="#38bdf8" />
              <circle cx="80%" cy="30%" r="4" fill="#f472b6" />
              <circle cx="50%" cy="50%" r="5" fill="#a855f7" />
              <circle cx="50%" cy="80%" r="4" fill="#f59e0b" />
            </svg>
          </div>

          <div className="relative z-10 max-w-2xl mx-auto space-y-6">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-indigo-200 dark:border-indigo-500/30 bg-white/90 dark:bg-slate-900/90 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
              <Sparkles className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
              <span>Document-Grounded Dialectic Engine</span>
            </div>

            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#0F172A] dark:text-white tracking-tight leading-tight">
              READY TO TEST YOUR DOCUMENT?
            </h2>

            <p className="text-base sm:text-lg text-slate-600 dark:text-slate-300 leading-relaxed max-w-xl mx-auto font-normal">
              Upload your research paper, legal brief, or technical proposal. Let opposing AI minds extract evidence, expose blind spots, and deliver an independent, citation-grounded evaluation.
            </p>

            <div className="pt-3 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link to="/debate" className="w-full sm:w-auto">
                <Button
                  size="lg"
                  className="w-full sm:w-auto px-8 py-3.5 text-base gap-2.5 font-bold shadow-xl shadow-indigo-600/30 bg-gradient-to-r from-indigo-600 via-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white border border-indigo-500/20"
                >
                  <span>START DOCUMENT DEBATE</span>
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
              <Link to="/documents" className="w-full sm:w-auto">
                <Button
                  variant="secondary"
                  size="lg"
                  className="w-full sm:w-auto font-semibold"
                >
                  BROWSE REPOSITORY
                </Button>
              </Link>
            </div>

            <p className="text-xs text-slate-500 dark:text-slate-400 pt-2 font-mono">
              Page-accurate citations • Document-bound extraction • Independent arbitration
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default FinalCTA;
