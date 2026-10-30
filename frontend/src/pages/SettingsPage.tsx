import React, { useState } from 'react';
import {
  Settings as SettingsIcon,
  Palette,
  Sliders,
  Cpu,
  Save,
  Check,
  Lock,
  Sun,
  Moon,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { useTheme } from '../context/ThemeContext';

export const SettingsPage: React.FC = () => {
  const [saved, setSaved] = useState(false);
  const { theme, setTheme } = useTheme();

  // Local preferences state
  const [proModel, setProModel] = useState<string>('gpt-4o');
  const [conModel, setConModel] = useState<string>('claude-3-5-sonnet');
  const [rounds, setRounds] = useState<number>(3);
  const [responseStyle, setResponseStyle] = useState<string>('Adversarial Dialectic');

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      {/* Header (Section 22) */}
      <div className="space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold uppercase tracking-wider shadow-sm">
          <SettingsIcon className="w-3.5 h-3.5" />
          <span>PREFERENCES & ENGINE</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-black text-[#0F172A] dark:text-white tracking-tight">
          SETTINGS
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Configure visual theme, default multi-agent models, and dialectic parameters.
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* 1. Appearance (Section 22: Dark, Light) */}
        <div className="glass-panel rounded-3xl p-6 sm:p-7 border border-slate-200/80 dark:border-white/10 shadow-md bg-white/95 dark:bg-[#070a16]/90 space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-slate-100 dark:border-white/10">
            <div className="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-500/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shadow-sm">
              <Palette className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                Appearance
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Visual theme and atmospheric interface styling
              </p>
            </div>
          </div>

          <div className="pt-2">
            <label className="block text-xs font-mono font-bold text-slate-700 dark:text-slate-300 mb-2">
              Color Theme:
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setTheme('dark')}
                className={`p-3.5 rounded-2xl border text-xs font-mono font-bold flex items-center justify-between transition-all ${
                  theme === 'dark'
                    ? 'bg-gradient-to-r from-indigo-950 to-slate-900 text-white border-indigo-500 shadow-lg shadow-indigo-950/50 ring-2 ring-indigo-500/30'
                    : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-800 hover:border-indigo-300'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Moon className="w-4 h-4 text-indigo-400" />
                  <span>Dark Mode (Recommended Default)</span>
                </div>
                {theme === 'dark' && <span className="w-2 h-2 rounded-full bg-indigo-400" />}
              </button>

              <button
                type="button"
                onClick={() => setTheme('light')}
                className={`p-3.5 rounded-2xl border text-xs font-mono font-bold flex items-center justify-between transition-all ${
                  theme === 'light'
                    ? 'bg-indigo-50 text-indigo-900 border-indigo-500 shadow-sm ring-2 ring-indigo-500/30'
                    : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-800 hover:border-indigo-300'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Sun className="w-4 h-4 text-amber-500" />
                  <span>Light Mode</span>
                </div>
                {theme === 'light' && <span className="w-2 h-2 rounded-full bg-indigo-600" />}
              </button>
            </div>
          </div>
        </div>

        {/* 2. Debate Preferences (Section 22: Debate rounds, Response style) */}
        <div className="glass-panel rounded-3xl p-6 sm:p-7 border border-slate-200/80 dark:border-white/10 shadow-md bg-white/95 dark:bg-[#070a16]/90 space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-slate-100 dark:border-white/10">
            <div className="w-8 h-8 rounded-xl bg-sky-50 dark:bg-sky-950/50 border border-sky-200 dark:border-sky-500/30 flex items-center justify-center text-sky-600 dark:text-sky-400 shadow-sm">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                Debate Preferences
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Number of adversarial rounds and response reasoning style
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div>
              <label className="block text-xs font-mono font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Default Debate Rounds:
              </label>
              <div className="flex gap-2">
                {[1, 3, 5].map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRounds(r)}
                    className={`flex-1 h-10 rounded-xl text-xs font-mono font-bold border transition-all ${
                      rounds === r
                        ? 'bg-indigo-600 text-white border-indigo-600 shadow-md shadow-indigo-600/25'
                        : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-800'
                    }`}
                  >
                    [ {r} ROUND{r > 1 ? 'S' : ''} ]
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Default Response Style:
              </label>
              <select
                value={responseStyle}
                onChange={(e) => setResponseStyle(e.target.value)}
                className="w-full h-10 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs text-slate-800 dark:text-slate-100 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/30 font-medium"
              >
                <option value="Adversarial Dialectic">Adversarial Dialectic (Formal Cross-Exam)</option>
                <option value="Empirical Inquest">Empirical Inquest (Citation Heavy)</option>
                <option value="Socratic Nuance">Socratic Nuance (Exploratory Bounds)</option>
              </select>
            </div>
          </div>
        </div>

        {/* 3. Model Preferences (Section 22: PRO model, CON model) */}
        <div className="glass-panel rounded-3xl p-6 sm:p-7 border border-slate-200/80 dark:border-white/10 shadow-md bg-white/95 dark:bg-[#070a16]/90 space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-slate-100 dark:border-white/10">
            <div className="w-8 h-8 rounded-xl bg-purple-50 dark:bg-purple-950/50 border border-purple-200 dark:border-purple-500/30 flex items-center justify-center text-purple-600 dark:text-purple-400 shadow-sm">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                Model Preferences
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Default foundation models for AI PRO and AI CON debaters
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div>
              <label className="block text-xs font-mono font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Default PRO Model:
              </label>
              <select
                value={proModel}
                onChange={(e) => setProModel(e.target.value)}
                className="w-full h-10 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs text-slate-800 dark:text-slate-100 shadow-sm focus:outline-none focus:ring-2 focus:ring-sky-500/40"
              >
                <option value="gpt-4o">OpenAI GPT-4o</option>
                <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                <option value="gemini-1-5-pro">Gemini 1.5 Pro</option>
                <option value="llama-3-3-70b">Meta Llama 3.3 70B</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Default CON Model:
              </label>
              <select
                value={conModel}
                onChange={(e) => setConModel(e.target.value)}
                className="w-full h-10 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs text-slate-800 dark:text-slate-100 shadow-sm focus:outline-none focus:ring-2 focus:ring-pink-500/40"
              >
                <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                <option value="gpt-4o">OpenAI GPT-4o</option>
                <option value="gemini-1-5-pro">Gemini 1.5 Pro</option>
                <option value="llama-3-3-70b">Meta Llama 3.3 70B</option>
              </select>
            </div>
          </div>
        </div>

        {/* 4. Future Settings (Section 22: Marked COMING SOON) */}
        <div className="glass-panel rounded-3xl p-6 border border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-[#070a16]/60 opacity-80 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200/60 dark:border-white/10">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-slate-400" />
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                Advanced Integrations
              </span>
            </div>
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-bold">
              COMING SOON
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-500 dark:text-slate-400">
            <div className="p-3 rounded-xl bg-slate-100/60 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-800">
              <span className="font-mono font-semibold block text-slate-700 dark:text-slate-300 mb-1">
                Custom API Keys (BYOK)
              </span>
              <span>Direct OpenAI, Anthropic, or OpenRouter endpoint connection.</span>
            </div>

            <div className="p-3 rounded-xl bg-slate-100/60 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-800">
              <span className="font-mono font-semibold block text-slate-700 dark:text-slate-300 mb-1">
                Local pgvector Knowledge Base
              </span>
              <span>Sync private PDF research papers and internal citation corpora.</span>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex items-center justify-end gap-3 pt-2">
          {saved && (
            <span className="text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-mono font-bold">
              <Check className="w-4 h-4" />
              Preferences saved
            </span>
          )}
          <Button
            type="submit"
            size="md"
            className="gap-2 font-bold px-7 shadow-md shadow-indigo-600/25 bg-gradient-to-r from-indigo-600 via-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white font-mono text-xs uppercase"
          >
            <Save className="w-4 h-4" />
            <span>Save Preferences</span>
          </Button>
        </div>
      </form>
    </div>
  );
};

export default SettingsPage;
