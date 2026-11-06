/**
 * Zenius ScreenPro — Institutional Authentication & Verification Portal.
 *
 * Professional, simple, and secure corporate authentication:
 * - Domain-restricted corporate login & self-registration (@zeniusit.com).
 * - Real email delivery: 6-digit OTP dispatched directly to corporate email inbox.
 * - Authenticated Forgot Password & Reset Password flows.
 * - Institutional green & white theme matching the screener dashboard.
 */

import React, { useState, useEffect } from 'react';
import {
  Lock,
  Mail,
  User,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle2,
  ShieldCheck,
  Clock,
  ArrowRight,
  KeyRound,
  RotateCcw,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export function LoginPage() {
  const {
    login,
    signup,
    verifyEmail,
    resendVerification,
    forgotPassword,
    resetPassword,
    authError,
    sessionTimedOut,
    clearAuthError,
  } = useAuth();

  // 'login' | 'signup' | 'verify' | 'forgot'
  const [mode, setMode] = useState('login');

  // Form Fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');

  // Password visibility
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  // Status feedback
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [clientError, setClientError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [forgotStep, setForgotStep] = useState(1); // 1: Email, 2: Code + New Password
  const [resendCooldown, setResendCooldown] = useState(0);

  // Resend cooldown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  const handleModeSwitch = (newMode) => {
    setMode(newMode);
    setClientError('');
    setSuccessMessage('');
    clearAuthError();
    if (newMode === 'forgot') {
      setForgotStep(1);
    }
  };

  // 1. Handle Login & Registration
  const handleSubmit = async (e) => {
    e.preventDefault();
    setClientError('');
    setSuccessMessage('');
    clearAuthError();

    const cleanEmail = email.trim().toLowerCase();

    // Enforce corporate domain
    if (!cleanEmail.endsWith('@zeniusit.com')) {
      setClientError('Access is strictly restricted to authorized @zeniusit.com corporate emails.');
      return;
    }

    if (mode === 'login') {
      if (!cleanEmail || !password) {
        setClientError('Please enter both corporate email and password.');
        return;
      }
      setIsSubmitting(true);
      try {
        await login(cleanEmail, password);
      } catch (err) {
        if (err.status === 403 || (err.message && err.message.toLowerCase().includes('not verified'))) {
          setMode('verify');
          setVerificationCode('');
          setSuccessMessage('Your account requires verification. Please enter the 6-digit verification code sent to your email.');
          setClientError('');
        }
      } finally {
        setIsSubmitting(false);
      }
    } else if (mode === 'signup') {
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

      setIsSubmitting(true);
      try {
        const res = await signup(cleanEmail, password, fullName.trim());
        if (res?.requiresVerification) {
          setMode('verify');
          setVerificationCode('');
          setSuccessMessage(res.message || `Verification code sent to ${cleanEmail}. Please check your inbox.`);
          setResendCooldown(30);
        }
      } catch (err) {
        if (err.status === 400 && err.message && err.message.toLowerCase().includes('already exists')) {
          setClientError('An account with this corporate email already exists. Please sign in below.');
        }
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  // 2. Handle OTP Verification
  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setClientError('');
    setSuccessMessage('');
    clearAuthError();

    const cleanCode = verificationCode.trim();
    if (!cleanCode || cleanCode.length < 6) {
      setClientError('Please enter the 6-digit verification code sent to your email.');
      return;
    }

    setIsSubmitting(true);
    try {
      await verifyEmail(email.trim().toLowerCase(), cleanCode);
    } catch (err) {
      // Handled by authError
    } finally {
      setIsSubmitting(false);
    }
  };

  // 3. Handle Resend Code
  const handleResend = async () => {
    if (resendCooldown > 0) return;
    setClientError('');
    setSuccessMessage('');
    clearAuthError();

    try {
      await resendVerification(email.trim().toLowerCase());
      setSuccessMessage('A fresh verification code has been dispatched to your corporate email. Please check your inbox and Junk folder.');
      setResendCooldown(30);
    } catch (err) {
      setClientError(err.message || 'Failed to resend code.');
    }
  };

  // 4. Handle Forgot Password (Step 1: Request Code)
  const handleForgotRequest = async (e) => {
    e.preventDefault();
    setClientError('');
    setSuccessMessage('');
    clearAuthError();

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.endsWith('@zeniusit.com')) {
      setClientError('Please enter a valid @zeniusit.com corporate email address.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await forgotPassword(cleanEmail);
      setSuccessMessage(res?.message || 'If registered, a 6-digit reset code has been sent to your email.');
      setForgotStep(2);
      setResetCode('');
      setResendCooldown(30);
    } catch (err) {
      setClientError(err.message || 'Failed to request password reset.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 5. Handle Reset Password (Step 2: Submit New Password)
  const handleResetSubmit = async (e) => {
    e.preventDefault();
    setClientError('');
    setSuccessMessage('');
    clearAuthError();

    const cleanCode = resetCode.trim();
    if (!cleanCode || cleanCode.length < 6) {
      setClientError('Please enter the 6-digit authorization code from your email.');
      return;
    }

    if (newPassword.length < 8) {
      setClientError('New password must be at least 8 characters long.');
      return;
    }
    if (!/[A-Za-z]/.test(newPassword) || !/[0-9]/.test(newPassword)) {
      setClientError('New password must contain both letters and numbers.');
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setClientError('New passwords do not match. Please verify.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await resetPassword(email.trim().toLowerCase(), cleanCode, newPassword);
      setSuccessMessage(res?.message || 'Password reset successful! Please sign in with your new password.');
      setPassword('');
      setNewPassword('');
      setConfirmNewPassword('');
      setResetCode('');
      setTimeout(() => {
        setMode('login');
      }, 2000);
    } catch (err) {
      setClientError(err.message || 'Password reset failed.');
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
      <div className="w-full max-w-[430px] relative z-10">
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

        {/* Crisp White Card Container */}
        <div className="bg-white border border-slate-200/90 rounded-2xl shadow-xl shadow-slate-200/70 p-7 sm:p-8">
          {/* Segmented Mode Switcher (Visible in Login & Signup modes) */}
          {(mode === 'login' || mode === 'signup') && (
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
          )}

          {/* Verification Header Banner */}
          {mode === 'verify' && (
            <div className="text-center mb-5">
              <div className="w-10 h-10 rounded-full bg-[#e1f0ed] text-[#147b73] mx-auto flex items-center justify-center mb-2.5">
                <KeyRound className="w-5 h-5" />
              </div>
              <h2 className="text-base font-bold text-slate-900">Corporate Email Verification</h2>
              <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">
                A 6-digit activation code was sent to:
                <br />
                <span className="font-semibold text-[#147b73]">{email}</span>
              </p>
              <p className="text-[11px] text-slate-500 mt-1">
                Please check your inbox (and Junk/Spam folder).
              </p>
            </div>
          )}

          {/* Forgot Password Header Banner */}
          {mode === 'forgot' && (
            <div className="text-center mb-5">
              <div className="w-10 h-10 rounded-full bg-[#fef3c7] text-[#b45309] mx-auto flex items-center justify-center mb-2.5">
                <Lock className="w-5 h-5" />
              </div>
              <h2 className="text-base font-bold text-slate-900">Reset Account Password</h2>
              <p className="text-xs text-slate-500 mt-1">
                {forgotStep === 1
                  ? 'Enter your corporate @zeniusit.com email to receive an authorization code.'
                  : 'Enter the 6-digit code received in your email and choose a new password.'}
              </p>
            </div>
          )}

          {/* Session Expiry Notification */}
          {sessionTimedOut && (
            <div className="mb-4 p-3 rounded-xl bg-amber-50 border border-amber-200 flex items-start space-x-2.5 text-amber-800 text-xs">
              <Clock className="w-4 h-4 shrink-0 mt-0.5 text-amber-600" />
              <div>
                <span className="font-semibold block">Session Expired</span>
                Your session was locked after 30 minutes of inactivity. Please sign in again.
              </div>
            </div>
          )}

          {/* Success Banner */}
          {successMessage && (
            <div className="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start space-x-2.5 text-emerald-800 text-xs">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-600" />
              <div>
                <span className="font-semibold block">Status</span>
                {successMessage}
              </div>
            </div>
          )}

          {/* Error Banner */}
          {displayedError && (
            <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 flex items-start space-x-2.5 text-rose-700 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
              <div>
                <span className="font-semibold block">Notice</span>
                {displayedError}
              </div>
            </div>
          )}

          {/* ============================================================= */}
          {/* 1. SIGN IN & SIGN UP FORM                                     */}
          {/* ============================================================= */}
          {(mode === 'login' || mode === 'signup') && (
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Full Name (Sign-up only) */}
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
                      placeholder="e.g. Manoj Kumar"
                      className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-hidden focus:border-[#147b73] focus:ring-2 focus:ring-[#147b73]/20 transition"
                    />
                  </div>
                </div>
              )}

              {/* Corporate Email Address */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600">
                    Corporate Email Address
                  </label>
                  <span className="text-[10px] font-medium text-[#147b73] bg-[#e1f0ed] px-2 py-0.5 rounded-full">
                    @zeniusit.com only
                  </span>
                </div>
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
                {mode === 'signup' && (
                  <p className="text-[10px] text-slate-500 mt-1">
                    An activation OTP code will be sent to confirm access to this corporate inbox.
                  </p>
                )}
              </div>

              {/* Password Field */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600">
                    Password
                  </label>
                  {mode === 'login' && (
                    <button
                      type="button"
                      onClick={() => handleModeSwitch('forgot')}
                      className="text-[11px] font-medium text-[#147b73] hover:text-[#0f675f] hover:underline cursor-pointer"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
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
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {mode === 'signup' && (
                  <p className="text-[10px] text-slate-500 mt-1">
                    Minimum 8 characters, including both letters and numbers.
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
                    >
                      {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              )}

              {/* Primary Action Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full mt-2 py-2.5 px-4 bg-[#147b73] hover:bg-[#0f675f] text-white font-bold text-xs rounded-xl shadow-sm hover:shadow-md transition flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>{mode === 'login' ? 'Authenticating...' : 'Sending Code...'}</span>
                  </>
                ) : (
                  <>
                    <span>{mode === 'login' ? 'Sign In' : 'Create & Verify Account'}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* ============================================================= */}
          {/* 2. OTP EMAIL VERIFICATION FORM                                */}
          {/* ============================================================= */}
          {mode === 'verify' && (
            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1.5 text-center">
                  Enter 6-Digit Code From Email
                </label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    maxLength={6}
                    autoFocus
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ''))}
                    placeholder="••••••"
                    className="w-full py-2.5 px-4 bg-white border border-slate-300 rounded-xl text-center text-xl font-mono font-bold tracking-[0.35em] text-slate-900 placeholder-slate-300 focus:outline-hidden focus:border-[#147b73] focus:ring-2 focus:ring-[#147b73]/20 transition"
                  />
                </div>
                <div className="flex items-center justify-between text-xs mt-2 px-1 text-slate-500">
                  <span>Code expires in 15 minutes</span>
                  <button
                    type="button"
                    disabled={resendCooldown > 0}
                    onClick={handleResend}
                    className="text-[#147b73] hover:text-[#0f675f] font-semibold disabled:text-slate-400 disabled:cursor-not-allowed cursor-pointer inline-flex items-center gap-1"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>{resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend Code'}</span>
                  </button>
                </div>
                <p className="text-[11px] text-slate-500 mt-2 text-center bg-slate-50 p-2 rounded-lg border border-slate-200">
                  Verification code dispatched to <strong>{email}</strong> via corporate email.<br />
                  Please check your <strong>Inbox</strong> & <strong>Junk / Spam</strong> folder.
                </p>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || verificationCode.length < 6}
                className="w-full mt-2 py-2.5 px-4 bg-[#147b73] hover:bg-[#0f675f] text-white font-bold text-xs rounded-xl shadow-sm hover:shadow-md transition flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Verifying Code...</span>
                  </>
                ) : (
                  <>
                    <span>Confirm & Activate Account</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>

              <div className="pt-2 text-center">
                <button
                  type="button"
                  onClick={() => handleModeSwitch('login')}
                  className="text-xs text-slate-500 hover:text-slate-800 font-medium cursor-pointer"
                >
                  ← Back to Sign In
                </button>
              </div>
            </form>
          )}

          {/* ============================================================= */}
          {/* 3. FORGOT PASSWORD WORKFLOW                                   */}
          {/* ============================================================= */}
          {mode === 'forgot' && forgotStep === 1 && (
            <form onSubmit={handleForgotRequest} className="space-y-4">
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                  Corporate Work Email
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

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full mt-2 py-2.5 px-4 bg-[#147b73] hover:bg-[#0f675f] text-white font-bold text-xs rounded-xl shadow-sm hover:shadow-md transition flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Dispatching Code...</span>
                  </>
                ) : (
                  <>
                    <span>Send Reset Authorization Code</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>

              <div className="pt-2 text-center">
                <button
                  type="button"
                  onClick={() => handleModeSwitch('login')}
                  className="text-xs text-slate-500 hover:text-slate-800 font-medium cursor-pointer"
                >
                  ← Back to Sign In
                </button>
              </div>
            </form>
          )}

          {mode === 'forgot' && forgotStep === 2 && (
            <form onSubmit={handleResetSubmit} className="space-y-4">
              {/* 6-Digit Code */}
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1.5 text-center">
                  6-Digit Code From Email
                </label>
                <input
                  type="text"
                  required
                  maxLength={6}
                  value={resetCode}
                  onChange={(e) => setResetCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="••••••"
                  className="w-full py-2.5 px-4 bg-white border border-slate-300 rounded-xl text-center text-xl font-mono font-bold tracking-[0.3em] text-slate-900 placeholder-slate-300 focus:outline-hidden focus:border-[#147b73] focus:ring-2 focus:ring-[#147b73]/20 transition"
                />
              </div>

              {/* New Password */}
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                  New Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-10 pr-10 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-hidden focus:border-[#147b73] focus:ring-2 focus:ring-[#147b73]/20 transition"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition cursor-pointer"
                    tabIndex={-1}
                  >
                    {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-[10px] text-slate-500 mt-1">
                  At least 8 characters with letters and numbers.
                </p>
              </div>

              {/* Confirm New Password */}
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                  Confirm New Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    required
                    value={confirmNewPassword}
                    onChange={(e) => setConfirmNewPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-300 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-hidden focus:border-[#147b73] focus:ring-2 focus:ring-[#147b73]/20 transition"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full mt-2 py-2.5 px-4 bg-[#147b73] hover:bg-[#0f675f] text-white font-bold text-xs rounded-xl shadow-sm hover:shadow-md transition flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Updating Password...</span>
                  </>
                ) : (
                  <>
                    <span>Confirm & Reset Password</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>

              <div className="pt-2 text-center">
                <button
                  type="button"
                  onClick={() => handleModeSwitch('login')}
                  className="text-xs text-slate-500 hover:text-slate-800 font-medium cursor-pointer"
                >
                  ← Back to Sign In
                </button>
              </div>
            </form>
          )}

          {/* Mode Switch Helper (Sign in / Sign up) */}
          {(mode === 'login' || mode === 'signup') && (
            <div className="mt-5 pt-4 border-t border-slate-100 text-center">
              {mode === 'login' ? (
                <p className="text-xs text-slate-500">
                  Don't have an analyst account?{' '}
                  <button
                    type="button"
                    onClick={() => handleModeSwitch('signup')}
                    className="text-[#147b73] hover:text-[#0f675f] font-semibold hover:underline cursor-pointer ml-1"
                  >
                    Register now
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
          )}
        </div>

        {/* Security / Institutional Footer */}
        <div className="flex items-center justify-center space-x-1.5 text-[11px] text-slate-500 mt-5">
          <ShieldCheck className="w-3.5 h-3.5 text-[#147b73]" />
          <span>Restricted to @zeniusit.com · 256-bit encrypted · Multi-user isolated</span>
        </div>
      </div>
    </div>
  );
}
