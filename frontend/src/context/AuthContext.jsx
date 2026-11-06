/**
 * Authentication Context.
 *
 * Central state and session management for Zenius ScreenPro:
 * - Persistent sessions via localStorage ('access_token').
 * - Automatic user profile hydration on page reload (GET /api/auth/me).
 * - Human activity tracking (mouse, typing, scroll, clicks) with a 30-minute idle lock.
 * - Background keep-alive heartbeat (POST /api/auth/ping) while actively working.
 * - Corporate domain email verification (@zeniusit.com) via 6-digit OTP.
 * - Forgot password and authenticated password change handlers.
 * - Global modal state for user profile details & password management.
 */

import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import {
  changePasswordApi,
  fetchMeApi,
  forgotPasswordApi,
  loginApi,
  logoutApi,
  pingSessionApi,
  resendVerificationApi,
  resetPasswordApi,
  signupApi,
  updateProfileApi,
  verifyEmailApi,
} from '../services/api';

const AuthContext = createContext(null);

// 30 minutes = 1,800,000 milliseconds
const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000;

// Periodic server ping interval while active (5 minutes)
const PING_INTERVAL_MS = 5 * 60 * 1000;

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('access_token') || null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState(null);
  const [sessionTimedOut, setSessionTimedOut] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  // References for tracking human activity & ping scheduling without re-triggering renders
  const lastActivityRef = useRef(Date.now());
  const lastPingRef = useRef(Date.now());

  // -------------------------------------------------------------------------
  // 1. Core Logout Handler
  // -------------------------------------------------------------------------
  const logout = useCallback(async (reason = null) => {
    const currentToken = localStorage.getItem('access_token');
    if (currentToken) {
      logoutApi(currentToken).catch(() => {});
    }

    localStorage.removeItem('access_token');
    try {
      const keysToRemove = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('screening_')) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach((k) => localStorage.removeItem(k));
    } catch {}
    setToken(null);
    setUser(null);
    setIsProfileModalOpen(false);

    if (window.location.pathname !== '/login') {
      window.history.pushState({}, '', '/login');
      window.dispatchEvent(new PopStateEvent('popstate'));
    }

    if (reason === 'inactivity') {
      console.warn('[Auth] Session timed out after 30 minutes of inactivity.');
      setSessionTimedOut(true);
    } else {
      setSessionTimedOut(false);
    }
  }, []);

  // -------------------------------------------------------------------------
  // 2. Initialize / Rehydrate Session on Mount
  // -------------------------------------------------------------------------
  useEffect(() => {
    let isMounted = true;

    async function initSession() {
      const savedToken = localStorage.getItem('access_token');
      if (!savedToken) {
        if (isMounted) setIsLoading(false);
        return;
      }

      try {
        const profile = await fetchMeApi(savedToken);
        if (isMounted && profile && profile.id) {
          setUser(profile);
          setToken(savedToken);
          lastActivityRef.current = Date.now();
          lastPingRef.current = Date.now();
        } else {
          throw new Error('Invalid profile data');
        }
      } catch (err) {
        console.warn('[Auth] Session rehydration check:', err.message);
        if (err.status === 401 || err.status === 403) {
          localStorage.removeItem('access_token');
          if (isMounted) {
            setUser(null);
            setToken(null);
          }
        } else {
          try {
            const base64Url = savedToken.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const payload = JSON.parse(window.atob(base64));
            const nowUnix = Math.floor(Date.now() / 1000);

            if (payload.exp && payload.exp < nowUnix) {
              localStorage.removeItem('access_token');
              if (isMounted) {
                setUser(null);
                setToken(null);
              }
            } else if (isMounted) {
              setUser({
                id: payload.sub,
                email: payload.email,
                full_name: payload.name || payload.email.split('@')[0],
                is_verified: true,
              });
              setToken(savedToken);
              lastActivityRef.current = Date.now();
              lastPingRef.current = Date.now();
            }
          } catch {
            localStorage.removeItem('access_token');
            if (isMounted) {
              setUser(null);
              setToken(null);
            }
          }
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    initSession();

    return () => {
      isMounted = false;
    };
  }, []);

  // -------------------------------------------------------------------------
  // 3. Human Inactivity Tracking
  // -------------------------------------------------------------------------
  useEffect(() => {
    if (!token || !user) return;

    let throttleTimer = null;

    const handleHumanInteraction = () => {
      const now = Date.now();
      if (!throttleTimer) {
        lastActivityRef.current = now;
        throttleTimer = setTimeout(() => {
          throttleTimer = null;
        }, 1000);
      }
    };

    const monitoredEvents = ['mousedown', 'keydown', 'scroll', 'touchstart', 'mousemove', 'click'];
    monitoredEvents.forEach((eventName) => {
      window.addEventListener(eventName, handleHumanInteraction, { passive: true });
    });

    const intervalId = setInterval(() => {
      const now = Date.now();
      const idleTime = now - lastActivityRef.current;

      if (idleTime >= INACTIVITY_TIMEOUT_MS) {
        logout('inactivity');
        return;
      }

      if (now - lastPingRef.current >= PING_INTERVAL_MS) {
        lastPingRef.current = now;
        pingSessionApi(token).catch((err) => {
          console.warn('[Auth] Background heartbeat failed:', err.message);
        });
      }
    }, 10000);

    return () => {
      monitoredEvents.forEach((eventName) => {
        window.removeEventListener(eventName, handleHumanInteraction);
      });
      clearInterval(intervalId);
      if (throttleTimer) clearTimeout(throttleTimer);
    };
  }, [token, user, logout]);

  // -------------------------------------------------------------------------
  // 4. Login Function
  // -------------------------------------------------------------------------
  const login = async (email, password) => {
    setAuthError(null);
    setSessionTimedOut(false);
    try {
      const res = await loginApi(email, password);
      if (res && res.access_token) {
        try {
          const keysToRemove = [];
          for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith('screening_')) {
              keysToRemove.push(key);
            }
          }
          keysToRemove.forEach((k) => localStorage.removeItem(k));
        } catch {}
        localStorage.setItem('access_token', res.access_token);
        setToken(res.access_token);
        setUser(res.user);
        lastActivityRef.current = Date.now();
        lastPingRef.current = Date.now();
        if (window.location.pathname === '/login') {
          window.history.pushState({}, '', '/');
          window.dispatchEvent(new PopStateEvent('popstate'));
        }
        return { success: true, user: res.user };
      }
      throw new Error('No access token received from server');
    } catch (err) {
      setAuthError(err.message || 'Login failed');
      throw err;
    }
  };

  // -------------------------------------------------------------------------
  // 5. Sign-Up Function
  // -------------------------------------------------------------------------
  const signup = async (email, password, fullName = '') => {
    setAuthError(null);
    setSessionTimedOut(false);
    try {
      const res = await signupApi(email, password, fullName);
      return {
        requiresVerification: true,
        email: res.email,
        message: res.message,
        verification_code: res.verification_code,
      };
    } catch (err) {
      setAuthError(err.message || 'Sign-up failed');
      throw err;
    }
  };

  // -------------------------------------------------------------------------
  // 6. Verify Email OTP Code
  // -------------------------------------------------------------------------
  const verifyEmail = async (email, code) => {
    setAuthError(null);
    try {
      const res = await verifyEmailApi(email, code);
      if (res && res.access_token) {
        localStorage.setItem('access_token', res.access_token);
        setToken(res.access_token);
        setUser(res.user);
        lastActivityRef.current = Date.now();
        lastPingRef.current = Date.now();
        if (window.location.pathname === '/login') {
          window.history.pushState({}, '', '/');
          window.dispatchEvent(new PopStateEvent('popstate'));
        }
        return { success: true, user: res.user };
      }
      throw new Error('Verification completed but no access token was returned.');
    } catch (err) {
      setAuthError(err.message || 'Email verification failed');
      throw err;
    }
  };

  // -------------------------------------------------------------------------
  // 7. Resend Verification Code
  // -------------------------------------------------------------------------
  const resendVerification = async (email) => {
    setAuthError(null);
    try {
      return await resendVerificationApi(email);
    } catch (err) {
      setAuthError(err.message || 'Failed to resend verification code');
      throw err;
    }
  };

  // -------------------------------------------------------------------------
  // 8. Forgot Password & Reset Password
  // -------------------------------------------------------------------------
  const forgotPassword = async (email) => {
    setAuthError(null);
    try {
      return await forgotPasswordApi(email);
    } catch (err) {
      setAuthError(err.message || 'Failed to request password reset');
      throw err;
    }
  };

  const resetPassword = async (email, code, newPassword) => {
    setAuthError(null);
    try {
      return await resetPasswordApi(email, code, newPassword);
    } catch (err) {
      setAuthError(err.message || 'Failed to reset password');
      throw err;
    }
  };

  // -------------------------------------------------------------------------
  // 9. Change Password (Authenticated In-App)
  // -------------------------------------------------------------------------
  const changePassword = async (currentPassword, newPassword) => {
    try {
      return await changePasswordApi(currentPassword, newPassword);
    } catch (err) {
      throw err;
    }
  };

  // -------------------------------------------------------------------------
  // 10. Update Profile (Display Name)
  // -------------------------------------------------------------------------
  const updateProfile = async (fullName) => {
    try {
      const updated = await updateProfileApi(fullName);
      if (updated) {
        setUser((prev) => ({ ...prev, full_name: updated.full_name }));
      }
      return updated;
    } catch (err) {
      throw err;
    }
  };

  const clearAuthError = () => setAuthError(null);
  const openProfileModal = () => setIsProfileModalOpen(true);
  const closeProfileModal = () => setIsProfileModalOpen(false);

  const value = {
    user,
    token,
    isAuthenticated: Boolean(user && token),
    isLoading,
    authError,
    sessionTimedOut,
    isProfileModalOpen,
    openProfileModal,
    closeProfileModal,
    login,
    signup,
    verifyEmail,
    resendVerification,
    forgotPassword,
    resetPassword,
    changePassword,
    updateProfile,
    logout,
    clearAuthError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
