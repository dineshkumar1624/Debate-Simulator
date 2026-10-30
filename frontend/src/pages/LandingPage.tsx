import React from 'react';
import { Hero } from '../components/landing/Hero';
import { QuickDebateInput } from '../components/landing/QuickDebateInput';
import { CompactWhyDebate } from '../components/landing/CompactWhyDebate';
import { FeaturesPreview } from '../components/landing/FeaturesPreview';
import { FinalCTA } from '../components/landing/FinalCTA';
import { IntroAnimation } from '../components/landing/IntroAnimation';
import { useIntro } from '../context/IntroContext';

export const LandingPage: React.FC = () => {
  const { showIntro, introKey, onIntroComplete } = useIntro();

  return (
    <>
      {/* 1. Full-screen Intro Overlay on initial launch or replay */}
      {showIntro && (
        <IntroAnimation key={introKey} onComplete={onIntroComplete} />
      )}

      {/* 2. Product Landing Page Dashboard:
          Completely hidden & suppressed during intro playback so the dashboard
          never competes with or shows behind the intro. Smoothly fades in once completed. */}
      <div
        className={`relative z-10 flex flex-col space-y-6 pb-12 transition-all duration-700 ${
          showIntro
            ? 'opacity-0 pointer-events-none scale-98 invisible h-0 overflow-hidden select-none'
            : 'opacity-100 pointer-events-auto scale-100 visible h-auto'
        }`}
        aria-hidden={showIntro}
      >
        {/* Hero Section with Signature 3D AI Debate Chamber */}
        <Hero />

        {/* Question Input Section */}
        <QuickDebateInput />

        {/* Short "Why Debate?" Section */}
        <CompactWhyDebate />

        {/* Short How It Works Preview */}
        <FeaturesPreview />

        {/* Start Debating CTA */}
        <FinalCTA />
      </div>
    </>
  );
};

export default LandingPage;
