/**
 * Zenius ScreenPro — Institutional Login & Analyst Registration Portal.
 *
 * Professional, simple, and executive authentication interface:
 * - Dual-mode: Sign In & Open Self-Registration.
 * - Password visibility toggle.
 * - Real-time client & server validation with clear error messaging.
 * - Session timeout notification banner.
 * - High-contrast institutional typography and gold accent branding.
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
    <div className="min-h-screen w-screen flex flex-col justify-center items-center bg-[#070c16] text-slate-100 p-4 relative overflow-hidden select-none font-sans">
      {/* Subtle Ambient Radial Lighting */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,rgba(229,164,32,0.08),rgba(7,12,22,0))]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_100%,rgba(13,28,49,0.7),rgba(7,12,22,0))]" />

      {/* Main Authentication Card */}
      <div className="w-full max-w-[410px] relative z-10">
        {/* Brand Header */}
        <div className="text-center mb-7">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#e5a420] text-[#070c16] font-bold text-xl shadow-lg shadow-amber-500/20 mb-3 ring-1 ring-white/20 tracking-tighter">
            Z
          </div>
          <div className="flex items-center justify-center space-x-1.5 text-2xl font-bold tracking-tight text-white">
            <span>Zenius</span>
            <span className="text-[#e5a420]">ScreenPro</span>
          </div>
          <p className="text-[12px] text-slate-400 mt-1 font-medium tracking-wide">
            Institutional Equity Screening & Analytics
          </p>
        </div>

        {/* Card Container */}
        <div className="bg-[#0d1626]/90 backdrop-blur-xl border border-slate-800/80 rounded-2xl shadow-2xl shadow-black/60 p-7">
          {/* Segmented Mode Switcher */}
          <div className="flex bg-[#060b14] p-1 rounded-xl mb-6 border border-slate-800/70">
            <button
              type="button"
              onClick={() => handleModeSwitch('login')}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                mode === 'login'
                  ? 'bg-[#15233a] text-white shadow-xs border border-slate-700/60'
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
                  ? 'bg-[#15233a] text-white shadow-xs border border-slate-700/60'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Inactivity Session Expiry Notification */}
          {sessionTimedOut && (
            <div className="mb-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start space-x-2.5 text-amber-300 text-xs">
              <Clock className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
              <div>
                <span className="font-semibold block">Session Expired</span>
                Your session was locked after 30 minutes of inactivity. Please sign in again.
              </div>
            </div>
          )}

          {/* Error Alert */}
          {displayedError && (
            <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start space-x-2.5 text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
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
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
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
                    className="w-full pl-10 pr-4 py-2.5 bg-[#060b14] border border-slate-700/70 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-hidden focus:border-[#e5a420] focus:ring-1 focus:ring-[#e5a420]/40 transition"
                  />
                </div>
              </div>
            )}

            {/* Email Field */}
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
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
                  placeholder="analyst@zeniusit.com"
                  className="w-full pl-10 pr-4 py-2.5 bg-[#060b14] border border-slate-700/70 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-hidden focus:border-[#e5a420] focus:ring-1 focus:ring-[#e5a420]/40 transition"
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
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
                  className="w-full pl-10 pr-10 py-2.5 bg-[#060b14] border border-slate-700/70 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-hidden focus:border-[#e5a420] focus:ring-1 focus:ring-[#e5a420]/40 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300 transition cursor-pointer"
                  tabIndex={-1}
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
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
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
                    className="w-full pl-10 pr-10 py-2.5 bg-[#060b14] border border-slate-700/70 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-hidden focus:border-[#e5a420] focus:ring-1 focus:ring-[#e5a420]/40 transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300 transition cursor-pointer"
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
              className="w-full mt-2 py-2.5 px-4 bg-[#e5a420] hover:bg-[#f3b028] text-[#070c16] font-bold text-xs rounded-xl shadow-md shadow-amber-500/10 flex items-center justify-center space-x-2 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-[#070c16]/30 border-t-[#070c16] rounded-full animate-spin" />
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
          <div className="mt-5 pt-4 border-t border-slate-800/80 text-center">
            {mode === 'login' ? (
              <p className="text-xs text-slate-400">
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => handleModeSwitch('signup')}
                  className="text-[#e5a420] hover:text-[#f3b028] font-semibold cursor-pointer ml-1"
                >
                  Create one now
                </button>
              </p>
            ) : (
              <p className="text-xs text-slate-400">
                Already registered?{' '}
                <button
                  type="button"
                  onClick={() => handleModeSwitch('login')}
                  className="text-[#e5a420] hover:text-[#f3b028] font-semibold cursor-pointer ml-1"
                >
                  Sign in here
                </button>
              </p>
            )}
          </div>
        </div>

        {/* Security / Institutional Footer */}
        <div className="flex items-center justify-center space-x-2 text-[11px] text-slate-500 mt-5">
          <ShieldCheck className="w-3.5 h-3.5 text-slate-500" />
          <span>256-bit encrypted · Session isolation active</span>
        </div>
      </div>
    </div>
  );
}
