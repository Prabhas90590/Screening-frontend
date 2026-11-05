/**
 * Lightweight Client-Side Router for Authentication & Core Views.
 *
 * Provides dedicated URL routing for '/login' while preserving 100% of the
 * existing in-memory tab switching (Screening Rules, Results, Schedule).
 *
 * Features:
 * - Real browser address bar sync ('http://localhost:5173/login' vs '/').
 * - Browser Back / Forward button support via 'popstate'.
 * - Zero risky third-party package additions.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

const RouterContext = createContext(null);

export function RouterProvider({ children }) {
  const [currentPath, setCurrentPath] = useState(() => window.location.pathname || '/');

  const navigate = useCallback((toPath, { replace = false } = {}) => {
    if (window.location.pathname !== toPath) {
      if (replace) {
        window.history.replaceState({}, '', toPath);
      } else {
        window.history.pushState({}, '', toPath);
      }
    }
    setCurrentPath(toPath);
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname || '/');
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const value = {
    currentPath,
    navigate,
    isLoginPage: currentPath === '/login',
  };

  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
}

export function useRouter() {
  const ctx = useContext(RouterContext);
  if (!ctx) {
    throw new Error('useRouter must be used within a RouterProvider');
  }
  return ctx;
}
