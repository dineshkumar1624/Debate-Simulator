import React, { createContext, useContext, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

interface IntroContextType {
  showIntro: boolean;
  introKey: number;
  replayIntro: () => void;
  onIntroComplete: () => void;
}

const IntroContext = createContext<IntroContextType | undefined>(undefined);

const SESSION_STORAGE_KEY = 'ai-debate-intro-seen';

export const IntroProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [introKey, setIntroKey] = useState<number>(0);

  // Check if intro was already seen in this browser session
  const [showIntro, setShowIntro] = useState<boolean>(() => {
    try {
      const hasSeen = sessionStorage.getItem(SESSION_STORAGE_KEY);
      // Show intro on initial website open if not seen in this session
      return !hasSeen && window.location.pathname === '/';
    } catch {
      return false;
    }
  });

  const onIntroComplete = useCallback(() => {
    try {
      sessionStorage.setItem(SESSION_STORAGE_KEY, 'true');
    } catch {
      // ignore
    }
    setShowIntro(false);
  }, []);

  const replayIntro = useCallback(() => {
    try {
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
    } catch {
      // ignore
    }
    // Instant scroll to top so intro takes clean full viewport control
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' as ScrollBehavior });
    setIntroKey((prev) => prev + 1);
    setShowIntro(true);
    if (location.pathname !== '/') {
      navigate('/');
    }
  }, [location.pathname, navigate]);

  return (
    <IntroContext.Provider value={{ showIntro, introKey, replayIntro, onIntroComplete }}>
      {children}
    </IntroContext.Provider>
  );
};

export const useIntro = (): IntroContextType => {
  const context = useContext(IntroContext);
  if (!context) {
    throw new Error('useIntro must be used within an IntroProvider');
  }
  return context;
};

export default IntroContext;
