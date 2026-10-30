import React from 'react';
import { Navbar } from './Navbar';
import { Footer } from './Footer';
import { BackgroundGlow } from '../common/BackgroundGlow';
import { useIntro } from '../../context/IntroContext';

interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const { showIntro } = useIntro();

  return (
    <div className="relative min-h-screen flex flex-col bg-[#FAFAFC] dark:bg-[#05060A] text-slate-900 dark:text-[#F8FAFC] selection:bg-indigo-500/25 selection:text-indigo-900 dark:selection:bg-indigo-500/35 dark:selection:text-indigo-200">
      {/* Background glow and subtle futuristic architectural environment */}
      <BackgroundGlow />

      {/* Sticky floating navigation bar (suppressed during Intro playback) */}
      <div
        className={`transition-opacity duration-500 ${
          showIntro ? 'opacity-0 pointer-events-none select-none' : 'opacity-100 pointer-events-auto'
        }`}
        aria-hidden={showIntro}
      >
        <Navbar />
      </div>

      {/* Main Content Area */}
      <main className="flex-1 relative z-10 transition-opacity duration-300">
        {children}
      </main>

      {/* Shared Footer (suppressed during Intro playback) */}
      <div
        className={`transition-opacity duration-500 ${
          showIntro ? 'opacity-0 pointer-events-none select-none' : 'opacity-100 pointer-events-auto'
        }`}
        aria-hidden={showIntro}
      >
        <Footer />
      </div>
    </div>
  );
};

export default AppLayout;
