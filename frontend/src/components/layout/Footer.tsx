import React from 'react';
import { Link } from 'react-router-dom';
import { Scale, Github, ArrowUpRight, RotateCcw } from 'lucide-react';
import { useIntro } from '../../context/IntroContext';

export const Footer: React.FC = () => {
  const { replayIntro } = useIntro();

  return (
    <footer className="relative border-t border-slate-200/70 dark:border-white/10 bg-white/70 dark:bg-[#05060A] text-slate-500 dark:text-slate-400 py-12 overflow-hidden z-10">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 mb-10">
          {/* Brand Info & Motto (Section 23) */}
          <div className="md:col-span-5 space-y-3">
            <Link to="/" className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-500/30 flex items-center justify-center shadow-sm">
                <Scale className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
              </div>
              <span className="font-mono font-bold text-slate-900 dark:text-white tracking-wider text-sm">
                AI DEBATE SIMULATOR
              </span>
            </Link>

            {/* Core Motto from Section 23 */}
            <div className="text-sm text-slate-700 dark:text-slate-300 font-medium leading-relaxed">
              <p>Ask less.</p>
              <p>Challenge more.</p>
              <p className="text-indigo-600 dark:text-indigo-400 font-bold">Reason better.</p>
            </div>

            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm pt-1">
              Multi-agent reasoning environment challenging ideas with opposing AI perspectives and independent arbitration.
            </p>
          </div>

          {/* Navigation Links (Section 23: Home, Debate, How It Works, History) */}
          <div className="md:col-span-3 space-y-2.5">
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
              Navigation
            </h4>
            <ul className="space-y-1.5 text-xs font-mono">
              <li>
                <Link to="/" className="text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                  Home
                </Link>
              </li>
              <li>
                <Link to="/debate" className="text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                  Debate
                </Link>
              </li>
              <li>
                <Link to="/how-it-works" className="text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                  How It Works
                </Link>
              </li>
              <li>
                <Link to="/history" className="text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                  History
                </Link>
              </li>
            </ul>
          </div>

          {/* Technical & Settings (Section 23: Architecture, GitHub, Settings) */}
          <div className="md:col-span-4 space-y-2.5">
            <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
              Technical & Preferences
            </h4>
            <ul className="space-y-1.5 text-xs font-mono">
              <li>
                <Link to="/how-it-works#behind-the-debate" className="text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors flex items-center gap-1">
                  <span>Architecture</span>
                </Link>
              </li>
              <li>
                <a
                  href="https://github.com"
                  target="_blank"
                  rel="noreferrer"
                  className="text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors inline-flex items-center gap-1"
                >
                  <Github className="w-3 h-3" />
                  <span>GitHub</span>
                  <ArrowUpRight className="w-2.5 h-2.5 opacity-60" />
                </a>
              </li>
              <li>
                <Link to="/settings" className="text-slate-600 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
                  Settings
                </Link>
              </li>
              <li className="pt-1">
                <button
                  type="button"
                  onClick={replayIntro}
                  className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 hover:underline transition-colors flex items-center gap-1.5 cursor-pointer font-medium"
                  title="Replay the AI reasoning intro animation"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Replay Intro</span>
                </button>
              </li>
            </ul>
          </div>
        </div>

        {/* Minimal Copyright */}
        <div className="pt-6 border-t border-slate-200/60 dark:border-white/10 flex flex-col sm:flex-row items-center justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400 gap-2">
          <p>© {new Date().getFullYear()} AI Debate Simulator. Next-Generation AI Product.</p>
          <div className="flex gap-4">
            <span>Bilateral Reasoner</span>
            <span>•</span>
            <span>Independent Arbitration</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
