import React, { useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { RouterProvider, useRouter } from './context/RouterContext';
import { ScreeningProvider, useScreening } from './context/ScreeningContext';
import { AppLayout } from './components/layout/AppLayout';
import { ResultsView } from './components/results/ResultsView';
import { ScheduleView } from './components/schedule/ScheduleView';
import { ScreeningRulesView } from './components/screening-rules/ScreeningRulesView';
import { LoginPage } from './components/auth/LoginPage';

const MainViewRouter = () => {
  const { activeNav } = useScreening();

  switch (activeNav) {
    case 'results':
      return <ResultsView />;
    case 'schedule':
      return <ScheduleView />;
    case 'rules':
      return <ScreeningRulesView />;
    default:
      return <ResultsView />;
  }
};

/**
 * Gatekeeper & Route Manager.
 *
 * Controls access and synchronizes browser URL:
 * - Dedicated URL routing for '/login'.
 * - Shows loading splash while verifying session on startup.
 * - Redirects unauthenticated users to '/login' in browser URL bar.
 * - Redirects logged-in users at '/login' back to root screener '/'.
 */
const ProtectedApp = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const { currentPath, navigate, isLoginPage } = useRouter();

  // Synchronize browser URL bar with authentication status
  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated && currentPath !== '/login') {
      navigate('/login', { replace: true });
    } else if (isAuthenticated && isLoginPage) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, isLoading, currentPath, isLoginPage, navigate]);

  // 1. Session verification splash
  if (isLoading) {
    return (
      <div className="min-h-screen w-screen flex flex-col items-center justify-center bg-[#0a1120] text-slate-300 select-none">
        <div className="w-9 h-9 border-3 border-blue-500/20 border-t-blue-500 rounded-full animate-spin mb-4" />
        <span className="text-xs uppercase tracking-widest font-semibold text-slate-400">
          Verifying Session · Zenius ScreenPro...
        </span>
      </div>
    );
  }

  // 2. Unauthenticated: Display Login & Registration Page at /login
  if (!isAuthenticated || isLoginPage) {
    return <LoginPage />;
  }

  // 3. Authenticated: Render the full Equity Screening Platform at /
  return (
    <ScreeningProvider>
      <AppLayout>
        <MainViewRouter />
      </AppLayout>
    </ScreeningProvider>
  );
};

export default function App() {
  return (
    <RouterProvider>
      <AuthProvider>
        <ProtectedApp />
      </AuthProvider>
    </RouterProvider>
  );
}
