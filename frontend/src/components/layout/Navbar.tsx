import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, ArrowRight, Sun, Moon, Settings as SettingsIcon } from 'lucide-react';
import { Button } from '../ui/Button';
import { useTheme } from '../../context/ThemeContext';

export const Navbar: React.FC = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  // Primary navigation (Section 3 & 37: Home, Documents, Debate, How It Works, History)
  const navLinks = [
    { label: 'Home', href: '/' },
    { label: 'Documents', href: '/documents' },
    { label: 'Debate', href: '/debate' },
    { label: 'How It Works', href: '/how-it-works' },
    { label: 'History', href: '/history' },
  ];

  // Mobile menu items
  const mobileNavLinks = [
    { label: 'Home', href: '/' },
    { label: 'Documents', href: '/documents' },
    { label: 'Debate', href: '/debate' },
    { label: 'How It Works', href: '/how-it-works' },
    { label: 'History', href: '/history' },
    { label: 'Settings', href: '/settings' },
  ];

  const isActive = (href: string) => {
    if (href === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(href);
  };

  return (
    <header className="sticky top-0 z-50 px-3 sm:px-6 pt-3 pb-2 transition-all duration-300">
      {/* Floating glass pill navigation bar */}
      <div
        className={`max-w-6xl mx-auto rounded-2xl transition-all duration-300 px-4 sm:px-6 py-2.5 flex items-center justify-between border ${
          isScrolled
            ? 'glass-nav bg-white/85 dark:bg-[#070a14]/85 border-slate-200/80 dark:border-white/10 shadow-lg shadow-slate-900/5 dark:shadow-black/50 backdrop-blur-xl'
            : 'glass-nav bg-white/70 dark:bg-[#070a14]/70 border-slate-200/60 dark:border-white/[0.08] shadow-sm backdrop-blur-xl'
        }`}
      >
        {/* Brand Logo */}
        <Link
          to="/"
          className="flex items-center gap-3 group focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded-lg p-1"
        >
          <div className="relative w-8 h-8 flex items-center justify-center">
            {/* Ambient glow behind logo */}
            <div className="absolute inset-0 bg-indigo-500/15 dark:bg-indigo-500/25 rounded-full blur-md group-hover:bg-indigo-500/30 transition-all duration-300" />
            <svg
              viewBox="0 0 44 44"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="w-full h-full relative z-10 transform transition-transform group-hover:scale-105 duration-300"
            >
              {/* Connector line from left PRO node to central JUDGE node */}
              <line
                x1="11"
                y1="22"
                x2="22"
                y2="14"
                stroke="#0284c7"
                strokeWidth="2"
                strokeDasharray="2 2"
                opacity="0.8"
              />
              {/* Connector line from right CON node to central JUDGE node */}
              <line
                x1="33"
                y1="22"
                x2="22"
                y2="14"
                stroke="#a855f7"
                strokeWidth="2"
                strokeDasharray="2 2"
                opacity="0.8"
              />
              {/* PRO node (Left - Electric Blue) */}
              <circle
                cx="11"
                cy="22"
                r="6.5"
                className="fill-sky-100 dark:fill-sky-950 stroke-sky-500"
                strokeWidth="2"
              />
              <circle cx="11" cy="22" r="2.5" className="fill-sky-600 dark:fill-sky-400" />

              {/* CON node (Right - Purple / Magenta) */}
              <circle
                cx="33"
                cy="22"
                r="6.5"
                className="fill-purple-100 dark:fill-purple-950 stroke-purple-500"
                strokeWidth="2"
              />
              <circle cx="33" cy="22" r="2.5" className="fill-purple-600 dark:fill-purple-400" />

              {/* Central Reasoning / Judge Node (Top - Neutral Violet) */}
              <circle
                cx="22"
                cy="14"
                r="5.5"
                className="fill-indigo-100 dark:fill-indigo-950 stroke-indigo-500"
                strokeWidth="2"
              />
              <circle cx="22" cy="14" r="2" className="fill-indigo-600 dark:fill-indigo-300" />
            </svg>
          </div>

          <div className="flex flex-col text-left">
            <span className="text-[13px] font-mono font-black tracking-wider text-slate-900 dark:text-white leading-tight">
              AI DEBATE
            </span>
            <span className="text-[9px] font-mono text-indigo-600 dark:text-indigo-400 tracking-widest uppercase leading-tight font-bold">
              SIMULATOR
            </span>
          </div>
        </Link>

        {/* Desktop Primary Navigation Links (Section 3: Home, Debate, How It Works, History) */}
        <nav className="hidden md:flex items-center gap-7">
          {navLinks.map((link) => {
            const active = isActive(link.href);
            return (
              <Link
                key={link.label}
                to={link.href}
                className={`text-xs font-mono uppercase tracking-wider transition-all duration-200 relative py-1 ${
                  active
                    ? 'text-indigo-600 dark:text-indigo-400 font-bold drop-shadow-[0_0_8px_rgba(99,102,241,0.5)] after:w-full after:h-[2px] after:bg-gradient-to-r after:from-sky-400 after:to-purple-500 after:absolute after:bottom-0 after:left-0'
                    : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white font-medium after:w-0 hover:after:w-full after:h-[2px] after:bg-indigo-500 after:absolute after:bottom-0 after:left-0 after:transition-all after:duration-200'
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Desktop Right Side: Theme Toggle | Settings Icon (⚙) | START A DEBATE → (Section 3 & 37) */}
        <div className="hidden md:flex items-center gap-3">
          {/* Theme Toggle */}
          <button
            type="button"
            onClick={toggleTheme}
            className="p-2 rounded-xl border transition-all duration-200 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-slate-100/70 hover:bg-slate-200/60 dark:bg-slate-800/60 dark:hover:bg-slate-700/60 border-slate-200/80 dark:border-white/10 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? (
              <Sun className="w-4 h-4 text-amber-400 hover:rotate-45 transition-transform duration-300" />
            ) : (
              <Moon className="w-4 h-4 text-indigo-600 hover:-rotate-12 transition-transform duration-300" />
            )}
          </button>

          {/* Settings Icon (⚙) */}
          <Link
            to="/settings"
            className={`p-2 rounded-xl border transition-all duration-200 ${
              isActive('/settings')
                ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border-indigo-300 dark:border-indigo-500/40 shadow-sm'
                : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-slate-100/70 hover:bg-slate-200/60 dark:bg-slate-800/60 dark:hover:bg-slate-700/60 border-slate-200/80 dark:border-white/10 shadow-sm'
            }`}
            title="Settings & Preferences"
            aria-label="Settings"
          >
            <SettingsIcon className="w-4 h-4 hover:rotate-90 transition-transform duration-300" />
          </Link>

          {/* START A DEBATE CTA */}
          <Link to="/debate">
            <Button
              size="sm"
              className="gap-2 bg-gradient-to-r from-indigo-600 via-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white font-bold text-xs tracking-wider shadow-md shadow-indigo-600/25 hover:shadow-lg hover:shadow-indigo-600/35 border border-indigo-500/20 transition-all duration-200"
            >
              <span>START A DEBATE</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </Link>
        </div>

        {/* Mobile Navigation Controls */}
        <div className="md:hidden flex items-center gap-2">
          {/* Mobile Theme Toggle */}
          <button
            type="button"
            onClick={toggleTheme}
            className="p-2 rounded-xl border transition-all duration-200 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-slate-100/70 hover:bg-slate-200/60 dark:bg-slate-800/60 dark:hover:bg-slate-700/60 border-slate-200/80 dark:border-white/10 shadow-sm"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-indigo-600" />
            )}
          </button>

          {/* Mobile Settings Shortcut */}
          <Link
            to="/settings"
            className="p-2 rounded-xl border text-slate-600 dark:text-slate-300 bg-slate-100/70 dark:bg-slate-800/60 border-slate-200/80 dark:border-white/10"
            aria-label="Settings"
          >
            <SettingsIcon className="w-4 h-4" />
          </Link>

          {/* Mobile Menu Hamburger */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? (
              <X className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            ) : (
              <Menu className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Drawer (Section 3 & 37) */}
      {mobileMenuOpen && (
        <div className="md:hidden max-w-6xl mx-auto mt-2 rounded-2xl glass-panel border border-slate-200/90 dark:border-white/10 px-4 pt-3 pb-5 space-y-3 shadow-2xl bg-white/95 dark:bg-[#070a14]/95 backdrop-blur-xl animate-fadeIn">
          <div className="flex flex-col space-y-1">
            {mobileNavLinks.map((link) => {
              const active = isActive(link.href);
              return (
                <Link
                  key={link.label}
                  to={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`text-sm font-mono font-medium px-3 py-2.5 rounded-xl transition-colors flex items-center justify-between ${
                    active
                      ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-bold'
                      : 'text-slate-700 dark:text-slate-200 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <span>{link.label}</span>
                  {active && <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 dark:bg-indigo-400" />}
                </Link>
              );
            })}

            {/* Mobile CTA (Section 3 & 37) */}
            <div className="pt-3 border-t border-slate-200 dark:border-white/10">
              <Link to="/debate" onClick={() => setMobileMenuOpen(false)}>
                <Button size="md" className="w-full justify-center gap-2 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white font-bold">
                  <span>START A DEBATE →</span>
                </Button>
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};

export default Navbar;
