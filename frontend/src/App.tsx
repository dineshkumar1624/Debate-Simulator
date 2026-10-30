import React, { useEffect } from 'react';
import { Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { IntroProvider } from './context/IntroContext';
import { DocumentProvider } from './context/DocumentContext';
import LandingPage from './pages/LandingPage';
import DebatePage from './pages/DebatePage';
import DocumentsPage from './pages/DocumentsPage';
import HowItWorksPage from './pages/HowItWorksPage';
import PipelinePage from './pages/PipelinePage';
import HistoryPage from './pages/HistoryPage';
import SettingsPage from './pages/SettingsPage';
import NotFoundPage from './pages/NotFoundPage';

// Scroll to top helper on route transitions
const ScrollToTop: React.FC = () => {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' as ScrollBehavior });
  }, [pathname]);

  return null;
};

export const App: React.FC = () => {
  return (
    <IntroProvider>
      <DocumentProvider>
        <AppLayout>
          <ScrollToTop />
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/debate" element={<DebatePage />} />
              <Route path="/documents" element={<DocumentsPage />} />
              <Route path="/how-it-works" element={<HowItWorksPage />} />
              <Route path="/pipeline" element={<PipelinePage />} />
              <Route path="/technology" element={<Navigate to="/how-it-works" replace />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              {/* 404 Fallback Route */}
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </ErrorBoundary>
        </AppLayout>
      </DocumentProvider>
    </IntroProvider>
  );
};

export default App;
