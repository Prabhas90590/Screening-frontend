/**
 * Institutional Login & Self-Sign-Up Page (Phase 6).
 *
 * Professional authentication portal for Equity Screening analysts:
 * - Dual-mode: Sign In & Open Self-Registration ("Create Account").
 * - Password visibility toggle (Show/Hide).
 * - Real-time client & server error alerts (with brute-force warning display).
 * - Automatic 30-minute inactivity session expiration banner.
 * - Loading spinners on submission.
 */

import React, { useState } from 'react';
import {
  Lock,
  Mail,
  User,
  Eye,
  EyeOff,
  AlertCircle,
  TrendingUp,
  ShieldCheck,
  Clock,
  ArrowRight,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export function LoginPage() {
  const { login, signup, authError, sessionTimedOut, clearAuthError } = useAuth();

  const [mode, setMode] = useState('login'); // 'login' | 'signup'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [clientError, setClientError] = useState('');

  // Switch between Login and Sign-Up modes
  const handleModeSwitch = (newMode) => {
    setMode(newMode);
    setClientError('');
    clearAuthError();
  };

  // Handle Form Submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setClientError('');
    clearAuthError();

    // Client-side validation
    if (!email.trim() || !password) {
      setClientError('Please enter both email and password.');
      return;
    }

    if (mode === 'signup') {
      if (!fullName.trim()) {
        setClientError('Please enter your full name.');
        return;
      }
      if (password.length < 8) {
        setClientError('Password must be at least 8 characters long.');
        return;
      }
      if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
        setClientError('Password must contain both letters and numbers.');
        return;
      }
      if (password !== confirmPassword) {
        setClientError('Passwords do not match. Please verify.');
        return;
      }
    }

    setIsSubmitting(true);
    try {
      if (mode === 'login') {
        await login(email.trim(), password);
      } else {
        await signup(email.trim(), password, fullName.trim());
      }
      // Successful auth will automatically trigger re-render in App.jsx via AuthContext
    } catch (err) {
      // Server error is already captured in AuthContext.authError
      console.warn('[LoginPage] Authentication error:', err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const displayedError = clientError || authError;

  return (
    <div className="min-h-screen w-screen flex flex-col justify-center items-center bg-[#0a1120] text-slate-100 p-4 relative overflow-hidden select-none">
      {/* Background Ambient Grid Glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(14,165,233,0.15),rgba(255,255,255,0))]" />
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Main Authentication Card */}
      <div className="w-full max-w-md relative z-10">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-cyan-500 shadow-lg shadow-blue-500/25 mb-4 ring-1 ring-white/20">
            <TrendingUp className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-serif font-bold text-white tracking-tight">
            Equity Screening Platform
          </h1>
          <p className="text-xs uppercase tracking-widest text-slate-400 mt-1 font-semibold">
            Institutional Research & Screening Portal
          </p>
        </div>

        {/* Card Body */}
        <div className="bg-[#111c30]/90 backdrop-blur-xl border border-slate-700/60 rounded-2xl shadow-2xl shadow-black/50 p-7">
          {/* Mode Switcher Tabs */}
          <div className="flex bg-[#0b1424] p-1 rounded-xl mb-6 border border-slate-800">
            <button
              type="button"
              onClick={() => handleModeSwitch('login')}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                mode === 'login'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => handleModeSwitch('signup')}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                mode === 'signup'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Inactivity Session Expiry Banner */}
          {sessionTimedOut && (
            <div className="mb-5 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start space-x-3 text-amber-300 text-xs animate-in fade-in">
              <Clock className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
              <div>
                <span className="font-semibold block">Session Timeout</span>
                Your session was locked due to 30 minutes of inactivity. Please sign in again to continue.
              </div>
            </div>
          )}

          {/* Error Banner */}
          {displayedError && (
            <div className="mb-5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start space-x-3 text-rose-300 text-xs animate-in fade-in">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
              <div>
                <span className="font-semibold block">Authentication Failed</span>
                {displayedError}
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name Field (Sign-up only) */}
            {mode === 'signup' && (
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Full Name
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Prabhas Muthyala"
                    className="w-full pl-10 pr-4 py-2.5 bg-[#0a1322] border border-slate-700/80 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  />
                </div>
              </div>
            )}

            {/* Email Field */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Work Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@firm.com"
                  className="w-full pl-10 pr-4 py-2.5 bg-[#0a1322] border border-slate-700/80 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-10 py-2.5 bg-[#0a1322] border border-slate-700/80 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300 transition"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {mode === 'signup' && (
                <p className="text-[10px] text-slate-400 mt-1">
                  At least 8 characters, including letters and numbers.
                </p>
              )}
            </div>

            {/* Confirm Password (Sign-up only) */}
            {mode === 'signup' && (
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Confirm Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-10 pr-10 py-2.5 bg-[#0a1322] border border-slate-700/80 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300 transition"
                    tabIndex={-1}
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 py-2.5 px-4 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-blue-500/20 flex items-center justify-center space-x-2 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>{mode === 'login' ? 'Authenticating...' : 'Creating Account...'}</span>
                </>
              ) : (
                <>
                  <span>{mode === 'login' ? 'Sign In to Portal' : 'Register Account'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>

          {/* Footer Toggle Link */}
          <div className="mt-6 pt-5 border-t border-slate-800 text-center">
            {mode === 'login' ? (
              <p className="text-xs text-slate-400">
                New analyst?{' '}
                <button
                  type="button"
                  onClick={() => handleModeSwitch('signup')}
                  className="text-blue-400 hover:text-blue-300 font-semibold cursor-pointer underline underline-offset-2 ml-1"
                >
                  Create an account
                </button>
              </p>
            ) : (
              <p className="text-xs text-slate-400">
                Already registered?{' '}
                <button
                  type="button"
                  onClick={() => handleModeSwitch('login')}
                  className="text-blue-400 hover:text-blue-300 font-semibold cursor-pointer underline underline-offset-2 ml-1"
                >
                  Sign in here
                </button>
              </p>
            )}
          </div>
        </div>

        {/* Security Assurance Badge */}
        <div className="flex items-center justify-center space-x-2 text-[11px] text-slate-500 mt-6">
          <ShieldCheck className="w-4 h-4 text-emerald-500/80" />
          <span>256-bit encrypted authentication · 30-min idle protection</span>
        </div>
      </div>
    </div>
  );
}
