/**
 * Email Screening Results & Analyst Decisions Modal.
 *
 * Enables analysts to dispatch the multi-tab Excel screening workbook
 * directly via email, automatically synchronizing all in-memory Keep / Drop
 * decisions, reason tags, and custom memo notes to PostgreSQL.
 */

import React, { useState, useEffect } from 'react';
import {
  X,
  Mail,
  Send,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  Building2,
  Loader2,
  Check,
  Info,
  Layers,
  ArrowRight,
} from 'lucide-react';
import { emailExportResultsApi } from '../../services/api';

export function EmailExportModal({
  isOpen,
  onClose,
  runId,
  profileName = 'Core Strategy',
  securities = [],
  userEmail = '',
  totalUniverseCount = null,
  onExportSuccess,
}) {
  const [recipientEmail, setRecipientEmail] = useState('');
  const [memoNote, setMemoNote] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successData, setSuccessData] = useState(null);

  // Initialize or reset recipient email when modal opens or userEmail changes
  useEffect(() => {
    if (isOpen) {
      setRecipientEmail(userEmail || '');
      setMemoNote('');
      setErrorMessage('');
      setSuccessData(null);
      setIsSubmitting(false);
    }
  }, [isOpen, userEmail]);

  if (!isOpen) return null;

  // Decision metrics breakdown
  const keepDecisions = (securities || []).filter((s) => s.decision === 'keep');
  const dropDecisions = (securities || []).filter((s) => s.decision === 'drop');
  const decidedCount = keepDecisions.length + dropDecisions.length;
  const totalCount = totalUniverseCount || securities?.length || 0;
  const top20Count = (securities || []).filter(
    (s) => s.rank !== null && s.rank !== undefined && s.rank >= 1 && s.rank <= 20
  ).length;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    const targetEmail = recipientEmail.trim();
    if (!targetEmail) {
      setErrorMessage('Please enter a recipient corporate email address.');
      return;
    }

    // Basic email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(targetEmail)) {
      setErrorMessage('Please enter a valid email address (e.g. analyst@zeniusit.com).');
      return;
    }

    if (!runId) {
      setErrorMessage(
        'No active screening run ID found. Please initiate or select a completed screening run first.'
      );
      return;
    }

    setIsSubmitting(true);

    try {
      // Gather in-memory analyst decisions to sync and include in the workbook
      const decisionsPayload = (securities || [])
        .filter((s) => s.decision === 'keep' || s.decision === 'drop')
        .map((s) => ({
          canonical_company_id: s.id,
          company_name: s.name,
          profile_name: profileName,
          decision: s.decision,
          decision_reason: s.decisionReason || '',
          decision_note: s.decisionNote || '',
          run_id: runId,
        }));

      const res = await emailExportResultsApi(runId, {
        recipient_email: targetEmail,
        profile_name: profileName,
        decisions: decisionsPayload,
        memo_note: memoNote.trim() || null,
      });

      setSuccessData({
        recipient: res.recipient || targetEmail,
        decisionsCount: res.decisions_count ?? decidedCount,
        message: res.message || `Screening results successfully emailed to ${targetEmail}`,
      });

      if (onExportSuccess) {
        onExportSuccess(res);
      }
    } catch (err) {
      console.error('[EmailExportModal] Export failed:', err);
      setErrorMessage(
        err.message || 'Failed to dispatch screening email. Please verify SMTP settings and try again.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs select-none"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-[520px] bg-white rounded-2xl border border-slate-200/90 shadow-2xl shadow-slate-900/20 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="bg-[#f3f6f9] px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-[#e1f0ed] text-[#147b73] flex items-center justify-center font-bold shadow-2xs shrink-0">
              <Mail className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">Export Excel to Email</h2>
              <p className="text-[11px] text-slate-500">
                Send multi-tab results & latest Keep/Drop decisions
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-7 h-7 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 flex items-center justify-center transition cursor-pointer"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
          {/* SUCCESS VIEW */}
          {successData ? (
            <div className="space-y-4 py-2">
              <div className="p-4 rounded-xl bg-emerald-50/80 border border-emerald-200 text-center space-y-2">
                <div className="w-12 h-12 mx-auto rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-bold text-emerald-950">
                  Export Dispatched Successfully!
                </h3>
                <p className="text-xs text-emerald-800 leading-relaxed">
                  The updated screening report and Excel workbook have been sent to:
                </p>
                <div className="inline-block px-3 py-1 bg-white rounded-lg border border-emerald-300 text-xs font-semibold text-emerald-900 font-mono shadow-2xs">
                  {successData.recipient}
                </div>
              </div>

              {/* Summary Stats */}
              <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">
                <div>
                  <span className="text-slate-500 block text-[11px]">Strategy Profile</span>
                  <span className="font-semibold text-slate-800 truncate block">
                    {profileName}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[11px]">Decisions Included</span>
                  <span className="font-semibold text-slate-800">
                    {successData.decisionsCount} updated decisions
                  </span>
                </div>
              </div>

              <div className="text-[11px] text-slate-500 flex items-center gap-1.5 justify-center">
                <FileSpreadsheet className="w-3.5 h-3.5 text-[#147b73]" />
                <span>Workbook includes Top 20, Near Misses & Master Universe sheets</span>
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="w-full py-2.5 px-4 bg-[#147b73] hover:bg-[#0f625c] text-white text-xs font-semibold rounded-lg shadow-xs transition-colors cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          ) : (
            /* FORM VIEW */
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Screening Context & Decision Counts */}
              <div className="p-3.5 rounded-xl bg-[#f8fcfb] border border-[#b2ded9]/70 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <Layers className="w-3.5 h-3.5 text-[#147b73] shrink-0" />
                    <span className="text-xs font-bold text-slate-800 truncate">
                      {profileName}
                    </span>
                  </div>
                  {runId && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                      Run #{runId.slice(0, 8)}
                    </span>
                  )}
                </div>

                {/* Decisions Status Badges */}
                <div className="grid grid-cols-3 gap-2 pt-1 border-t border-[#b2ded9]/50 text-center">
                  <div className="p-2 rounded-lg bg-white/80 border border-slate-200/80 shadow-2xs">
                    <span className="text-[10px] uppercase font-semibold text-slate-500 block">
                      Evaluated
                    </span>
                    <span className="text-xs font-bold text-slate-800">{totalCount}</span>
                  </div>
                  <div className="p-2 rounded-lg bg-emerald-50/70 border border-emerald-200 text-emerald-800 shadow-2xs">
                    <span className="text-[10px] uppercase font-semibold text-emerald-700 block">
                      ✓ Kept
                    </span>
                    <span className="text-xs font-bold text-emerald-900">
                      {keepDecisions.length}
                    </span>
                  </div>
                  <div className="p-2 rounded-lg bg-rose-50/70 border border-rose-200 text-rose-800 shadow-2xs">
                    <span className="text-[10px] uppercase font-semibold text-rose-700 block">
                      ✕ Dropped
                    </span>
                    <span className="text-xs font-bold text-rose-900">
                      {dropDecisions.length}
                    </span>
                  </div>
                </div>

                <p className="text-[11px] text-slate-600 leading-tight">
                  {decidedCount > 0 ? (
                    <span>
                      <strong className="text-slate-800">{decidedCount}</strong> analyst Keep/Drop{' '}
                      {decidedCount === 1 ? 'decision' : 'decisions'} will be permanently saved to
                      the database and populated in the attached Excel workbook.
                    </span>
                  ) : (
                    <span className="text-slate-500">
                      No decisions selected yet. The default screening rankings will be exported.
                    </span>
                  )}
                </p>
              </div>

              {/* Recipient Email Field */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-800 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-slate-500" />
                    <span>Recipient Email Address</span>
                  </span>
                  <span className="text-[10px] text-slate-500 font-normal">
                    (Defaults to your corporate login)
                  </span>
                </label>
                <div className="relative">
                  <input
                    type="email"
                    required
                    value={recipientEmail}
                    onChange={(e) => setRecipientEmail(e.target.value)}
                    placeholder="analyst@zeniusit.com"
                    className="w-full px-3.5 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#147b73] focus:border-transparent transition"
                  />
                </div>
                <p className="text-[11px] text-slate-500">
                  You can specify another corporate colleague or investment committee recipient.
                </p>
              </div>

              {/* Optional Executive Memo / Analyst Note */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-800 flex items-center justify-between">
                  <span>Analyst Executive Memo (Optional)</span>
                  <span className="text-[10px] text-slate-500 font-normal">
                    Included in email body
                  </span>
                </label>
                <textarea
                  rows={3}
                  value={memoNote}
                  onChange={(e) => setMemoNote(e.target.value)}
                  placeholder="e.g. Q3 Rebalance approved. Kept high-scoring cash compounders; dropped candidates with margin contraction."
                  className="w-full px-3.5 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#147b73] focus:border-transparent transition resize-none"
                />
              </div>

              {/* Info Callout */}
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-600 space-y-1">
                <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                  <FileSpreadsheet className="w-3.5 h-3.5 text-[#e5a83b]" />
                  <span>Attached Excel Workbook Details:</span>
                </div>
                <ul className="list-disc list-inside space-y-0.5 text-slate-600 pl-1">
                  <li>Dedicated sheets: Top 20 Portfolio, Near Misses & Full Universe</li>
                  <li>Updated columns: Category, Rank, Decision, Decision Reason, Status/Note</li>
                  <li>Formatted HTML scorecard embedded directly in email</li>
                </ul>
              </div>

              {/* Error Banner */}
              {errorMessage && (
                <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isSubmitting}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#147b73] hover:bg-[#0f625c] disabled:opacity-60 text-white text-xs font-semibold rounded-lg shadow-2xs transition-colors cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Sending Email...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      <span>Send Excel to Mail</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
export default EmailExportModal;
