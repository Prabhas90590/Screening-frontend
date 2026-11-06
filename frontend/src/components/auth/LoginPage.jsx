/**
 * Zenius ScreenPro — Institutional Login & Analyst Registration Portal.
 *
 * Professional, simple, and clean authentication interface:
 * - Institutional green & white theme matching the Screener dashboard.
 * - Primary brand teal/green: #147b73 with crisp white cards and #f3f6f9 canvas.
 * - Dual-mode: Sign In & Open Self-Registration.
 * - Password visibility toggle.
 * - Real-time client & server validation with clear error messaging.
 * - Inactivity session timeout notification banner.
 * - Gold emblem and institutional security assurance badge.
 */

import React, { useState } from 'react';
import {
  Lock,
  Mail,
  User,
  Eye,
  EyeOff,
  AlertCircle,
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
    } catch (err) {
      console.warn('[LoginPage] Authentication error:', err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const displayedError = clientError || authError;

  return (
    <div className="min-h-screen w-screen flex flex-col justify-center items-center bg-[#f3f6f9] text-slate-800 p-4 relative overflow-hidden select-none font-sans">
      {/* Subtle Institutional Brand Ambient Glow */}
      <div
        className="absolute inset-0 pointer-events-none opacity-60"
        style={{
          background: 'radial-gradient(ellipse 70% 50% at 50% 0%, rgba(20, 123, 115, 0.08) 0%, rgba(243, 246, 249, 0) 100%)',
        }}
      />
      <div
        className="absolute inset-0 pointer-events-none opacity-40"
        style={{
          background: 'radial-gradient(ellipse 50% 40% at 50% 100%, rgba(35, 140, 131, 0.06) 0%, rgba(243, 246, 249, 0) 100%)',
        }}
      />

      {/* Main Authentication Container */}
      <div className="w-full max-w-[420px] relative z-10">
        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#e5a420] text-[#0d1c31] font-bold text-xl shadow-sm mb-3 tracking-tight">
            Z
          </div>
          <div className="flex items-center justify-center space-x-1.5 text-2xl font-bold tracking-tight text-slate-900">
            <span>Zenius</span>
            <span className="text-[#147b73]">ScreenPro</span>
          </div>
          <p className="text-[12px] text-slate-500 mt-1 font-medium tracking-wide">
            Institutional Equity Screening & Analytics
          </p>
        </div>

        {/* Crisp White Card */}
        <div className="bg-white border border-slate-200/90 rounded-2xl shadow-xl shadow-slate-200/70 p-7 sm:p-8">
          {/* Segmented Mode Switcher */}
          <div className="flex bg-[#eef3f6] p-1 rounded-xl mb-6 border border-slate-200/80">
            <button
              type="button"
              onClick={() => handleModeSwitch('login')}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                mode === 'login'
                  ? 'bg-white text-[#147b73] font-bold shadow-xs border border-slate-200/80'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => handleModeSwitch('signup')}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                mode === 'signup'
                  ? 'bg-white text-[#147b73] font-bold shadow-xs border border-slate-200/80'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Inactivity Session Expiry Notification */}
          {sessionTimedOut && (
            <div className="mb-4 p-3 rounded-xl bg-amber-50 border border-amber-200 flex items-start space-x-2.5 text-amber-800 text-xs">
              <Clock className="w-4 h-4 shrink-0 mt-0.5 text-amber-600" />
              <div>
                <span className="font-semibold block">Session Expired</span>
                Your session was locked after 30 minutes of inactivity. Please sign in again.
              </div>
            </div>
          )}

          {/* Error Alert */}
          {displayedError && (
            <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 flex items-start space-x-2.5 text-rose-700 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
              <div>
                <span className="font-semibold block">Authentication Error</span>
                {displayedError}
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name Field (Sign-up only) */}
            {mode === 'signup' && (
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                  Full Name
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Prabhas Muthyala"
                    className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-hidden focus:border-[#147b73] focus:ring-2 focus:ring-[#147b73]/20 transition"
                  />
                </div>
              </div>
            )}

            {/* Email Field */}
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                Work Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@zeniusit.com"
                  className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-hidden focus:border-[#147b73] focus:ring-2 focus:ring-[#147b73]/20 transition"
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-10 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-hidden focus:border-[#147b73] focus:ring-2 focus:ring-[#147b73]/20 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition cursor-pointer"
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {mode === 'signup' && (
                <p className="text-[10px] text-slate-500 mt-1">
                  Minimum 8 characters, including letters and numbers.
                </p>
              )}
            </div>

            {/* Confirm Password (Sign-up only) */}
            {mode === 'signup' && (
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                  Confirm Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-10 pr-10 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-hidden focus:border-[#147b73] focus:ring-2 focus:ring-[#147b73]/20 transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition cursor-pointer"
                    tabIndex={-1}
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
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
              className="w-full mt-2 py-2.5 px-4 bg-[#147b73] hover:bg-[#0f675f] text-white font-bold text-xs rounded-xl shadow-sm hover:shadow-md transition flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>{mode === 'login' ? 'Authenticating...' : 'Registering...'}</span>
                </>
              ) : (
                <>
                  <span>{mode === 'login' ? 'Sign In' : 'Create Account'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>

          {/* Mode Switch Helper */}
          <div className="mt-5 pt-4 border-t border-slate-100 text-center">
            {mode === 'login' ? (
              <p className="text-xs text-slate-500">
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => handleModeSwitch('signup')}
                  className="text-[#147b73] hover:text-[#0f675f] font-semibold hover:underline cursor-pointer ml-1"
                >
                  Create one now
                </button>
              </p>
            ) : (
              <p className="text-xs text-slate-500">
                Already registered?{' '}
                <button
                  type="button"
                  onClick={() => handleModeSwitch('login')}
                  className="text-[#147b73] hover:text-[#0f675f] font-semibold hover:underline cursor-pointer ml-1"
                >
                  Sign in here
                </button>
              </p>
            )}
          </div>
        </div>

        {/* Security / Institutional Footer */}
        <div className="flex items-center justify-center space-x-1.5 text-[11px] text-slate-500 mt-5">
          <ShieldCheck className="w-3.5 h-3.5 text-[#147b73]" />
          <span>256-bit encrypted · Session isolation active</span>
        </div>
      </div>
    </div>
  );
}
