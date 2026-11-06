/**
 * User Profile & Security Details Modal.
 *
 * Post-login analyst profile dialog:
 * - Displays Full Name, Corporate Email (@zeniusit.com), Verification status.
 * - Allows updating display name.
 * - In-app Password Reset / Change form with real-time feedback.
 * - Institutional green & white theme matching Zenius ScreenPro.
 */

import React, { useState } from 'react';
import {
  X,
  User,
  Mail,
  ShieldCheck,
  Lock,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Building2,
  Clock,
  KeyRound,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export function UserProfileModal() {
  const {
    user,
    isProfileModalOpen,
    closeProfileModal,
    changePassword,
    updateProfile,
    logout,
  } = useAuth();

  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'password'

  // Profile Edit
  const [isEditingName, setIsEditingName] = useState(false);
  const [nameInput, setNameInput] = useState(user?.full_name || '');
  const [nameError, setNameError] = useState('');
  const [nameSuccess, setNameSuccess] = useState('');
  const [isSavingName, setIsSavingName] = useState(false);

  // Password Change
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [isSubmittingPassword, setIsSubmittingPassword] = useState(false);

  if (!isProfileModalOpen || !user) return null;

  // Initials for avatar
  const initials = (user.full_name || user.email || 'A')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((n) => n[0].toUpperCase())
    .join('');

  // Handle Name Update
  const handleSaveName = async (e) => {
    e.preventDefault();
    setNameError('');
    setNameSuccess('');

    if (!nameInput.trim()) {
      setNameError('Name cannot be empty.');
      return;
    }

    setIsSavingName(true);
    try {
      await updateProfile(nameInput.trim());
      setNameSuccess('Profile name updated successfully.');
      setIsEditingName(false);
    } catch (err) {
      setNameError(err.message || 'Failed to update name.');
    } finally {
      setIsSavingName(false);
    }
  };

  // Handle In-App Password Change
  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');

    if (!currentPassword) {
      setPasswordError('Please enter your current password.');
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters long.');
      return;
    }

    if (!/[A-Za-z]/.test(newPassword) || !/[0-9]/.test(newPassword)) {
      setPasswordError('New password must contain both letters and numbers.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match. Please verify.');
      return;
    }

    setIsSubmittingPassword(true);
    try {
      const res = await changePassword(currentPassword, newPassword);
      setPasswordSuccess(res?.message || 'Password updated successfully.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setPasswordError(err.message || 'Failed to update password.');
    } finally {
      setIsSubmittingPassword(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs select-none"
      onClick={closeProfileModal}
    >
      <div
        className="relative w-full max-w-[460px] bg-white rounded-2xl border border-slate-200/90 shadow-2xl shadow-slate-900/15 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="bg-[#f3f6f9] px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-[#e1f0ed] text-[#147b73] flex items-center justify-center font-bold text-sm">
              <User className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">Analyst Profile & Security</h2>
              <p className="text-[11px] text-slate-500">Corporate Account Details</p>
            </div>
          </div>
          <button
            type="button"
            onClick={closeProfileModal}
            className="w-7 h-7 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 flex items-center justify-center transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-slate-200 bg-white px-6 pt-3">
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            className={`pb-2.5 text-xs font-semibold border-b-2 transition-colors cursor-pointer mr-6 ${
              activeTab === 'overview'
                ? 'border-[#147b73] text-[#147b73]'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Profile Details
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('password')}
            className={`pb-2.5 text-xs font-semibold border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'password'
                ? 'border-[#147b73] text-[#147b73]'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <KeyRound className="w-3.5 h-3.5" />
            <span>Reset Password</span>
          </button>
        </div>

        {/* Body Content */}
        <div className="p-6">
          {/* TAB 1: PROFILE DETAILS OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-4">
              {/* User Identity Card */}
              <div className="flex items-center space-x-4 p-4 rounded-xl bg-[#f8fcfb] border border-[#b2ded9]/60">
                <div className="w-13 h-13 rounded-xl bg-[#147b73] text-white flex items-center justify-center font-bold text-lg shadow-xs shrink-0">
                  {initials}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-slate-900 truncate">
                      {user.full_name || 'Institutional Analyst'}
                    </h3>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#e1f0ed] text-[#147b73] border border-[#b2ded9]">
                      <CheckCircle2 className="w-3 h-3 text-[#147b73]" />
                      Verified
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 truncate mt-0.5">{user.email}</p>
                  <p className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-1">
                    <Building2 className="w-3 h-3 text-slate-400" />
                    <span>Zenius Technologies · Equity Screening</span>
                  </p>
                </div>
              </div>

              {/* Status & Name Change */}
              {nameSuccess && (
                <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>{nameSuccess}</span>
                </div>
              )}
              {nameError && (
                <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
                  <span>{nameError}</span>
                </div>
              )}

              {/* Edit Display Name */}
              {isEditingName ? (
                <form onSubmit={handleSaveName} className="space-y-3 pt-1">
                  <div>
                    <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1">
                      Display Name
                    </label>
                    <input
                      type="text"
                      required
                      value={nameInput}
                      onChange={(e) => setNameInput(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-xs text-slate-900 focus:outline-hidden focus:border-[#147b73] focus:ring-1 focus:ring-[#147b73]/20"
                    />
                  </div>
                  <div className="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setIsEditingName(false)}
                      className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 border border-slate-300 rounded-lg cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSavingName}
                      className="px-3 py-1.5 text-xs font-semibold bg-[#147b73] hover:bg-[#0f675f] text-white rounded-lg cursor-pointer"
                    >
                      {isSavingName ? 'Saving...' : 'Save Name'}
                    </button>
                  </div>
                </form>
              ) : (
                <div className="flex items-center justify-between py-2 border-t border-slate-100 text-xs">
                  <div>
                    <span className="text-slate-500">Analyst Name: </span>
                    <span className="font-semibold text-slate-800">{user.full_name || 'Not set'}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setNameInput(user.full_name || '');
                      setIsEditingName(true);
                    }}
                    className="text-[#147b73] hover:text-[#0f675f] font-semibold hover:underline cursor-pointer"
                  >
                    Edit Name
                  </button>
                </div>
              )}

              {/* Security Metrics */}
              <div className="space-y-2 pt-2 border-t border-slate-100 text-xs">
                <div className="flex items-center justify-between text-slate-600">
                  <span className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <span>Session Idle Lock:</span>
                  </span>
                  <span className="font-semibold text-slate-800">30 minutes</span>
                </div>
                <div className="flex items-center justify-between text-slate-600">
                  <span className="flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Corporate Domain:</span>
                  </span>
                  <span className="font-semibold text-emerald-700">@zeniusit.com</span>
                </div>
              </div>

              {/* Quick Switch to Reset Password */}
              <div className="pt-3">
                <button
                  type="button"
                  onClick={() => setActiveTab('password')}
                  className="w-full py-2 px-3 text-xs font-semibold border border-[#147b73] text-[#147b73] hover:bg-[#f0f9f8] rounded-xl transition flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Lock className="w-3.5 h-3.5" />
                  <span>Reset / Change Password</span>
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: RESET / CHANGE PASSWORD */}
          {activeTab === 'password' && (
            <form onSubmit={handleChangePassword} className="space-y-3.5">
              <div className="p-3 rounded-xl bg-[#f0f9f8] border border-[#b2ded9] text-xs text-[#0f675f]">
                <strong>Password Security Policy:</strong> Choose a strong password with at least 8 characters, containing both letters and numbers.
              </div>

              {/* Success Notification */}
              {passwordSuccess && (
                <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>{passwordSuccess}</span>
                </div>
              )}

              {/* Error Notification */}
              {passwordError && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
                  <span>{passwordError}</span>
                </div>
              )}

              {/* Current Password */}
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Current Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-3.5 h-3.5" />
                  </div>
                  <input
                    type={showCurrentPassword ? 'text' : 'password'}
                    required
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Enter current password"
                    className="w-full pl-9 pr-9 py-2 bg-white border border-slate-300 rounded-lg text-xs text-slate-900 focus:outline-hidden focus:border-[#147b73] focus:ring-1 focus:ring-[#147b73]/20"
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 cursor-pointer"
                    tabIndex={-1}
                  >
                    {showCurrentPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* New Password */}
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  New Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-3.5 h-3.5" />
                  </div>
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    className="w-full pl-9 pr-9 py-2 bg-white border border-slate-300 rounded-lg text-xs text-slate-900 focus:outline-hidden focus:border-[#147b73] focus:ring-1 focus:ring-[#147b73]/20"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 cursor-pointer"
                    tabIndex={-1}
                  >
                    {showNewPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* Confirm New Password */}
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Confirm New Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-3.5 h-3.5" />
                  </div>
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repeat new password"
                    className="w-full pl-9 pr-3 py-2 bg-white border border-slate-300 rounded-lg text-xs text-slate-900 focus:outline-hidden focus:border-[#147b73] focus:ring-1 focus:ring-[#147b73]/20"
                  />
                </div>
              </div>

              {/* Submit Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isSubmittingPassword}
                  className="w-full py-2.5 px-4 bg-[#147b73] hover:bg-[#0f675f] text-white font-bold text-xs rounded-xl shadow-sm transition flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  {isSubmittingPassword ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Updating Password...</span>
                    </>
                  ) : (
                    <span>Update & Save Password</span>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Footer */}
        <div className="bg-[#f8fafc] px-6 py-3 border-t border-slate-200 flex items-center justify-between text-xs">
          <button
            type="button"
            onClick={() => logout()}
            className="text-rose-600 hover:text-rose-700 font-semibold cursor-pointer"
          >
            Sign Out
          </button>
          <button
            type="button"
            onClick={closeProfileModal}
            className="px-4 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
