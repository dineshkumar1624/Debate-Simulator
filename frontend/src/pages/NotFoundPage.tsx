import React from 'react';
import { Link } from 'react-router-dom';
import { Scale, ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/Button';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="relative z-10 max-w-xl mx-auto px-4 sm:px-6 py-24 text-center">
      <div className="glass-panel rounded-3xl p-10 sm:p-14 border border-slate-200/90 dark:border-white/10 shadow-2xl bg-white/95 dark:bg-[#080d1e]/90 space-y-6">
        {/* Visual Icon */}
        <div className="w-20 h-20 rounded-3xl bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-500/30 flex items-center justify-center mx-auto text-indigo-600 dark:text-indigo-400 shadow-md">
          <Scale className="w-10 h-10" />
        </div>

        {/* 404 Code */}
        <div className="space-y-2">
          <span className="text-5xl sm:text-6xl font-black font-mono tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 dark:from-sky-400 dark:via-indigo-300 dark:to-pink-400">
            404
          </span>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
            Looks like this debate went off-topic.
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 max-w-sm mx-auto leading-relaxed">
            The page or debate transcript you are attempting to access does not exist or has been relocated in the reasoning graph.
          </p>
        </div>

        {/* Button */}
        <div className="pt-2">
          <Link to="/">
            <Button
              size="lg"
              className="gap-2.5 font-bold px-8 shadow-lg shadow-indigo-600/25 bg-gradient-to-r from-indigo-600 via-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>BACK TO HOME</span>
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default NotFoundPage;
