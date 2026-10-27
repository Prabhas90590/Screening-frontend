import React, { useState, useEffect } from 'react';
import { AlertCircle, ArrowUpRight, CheckCircle2, ChevronRight, HelpCircle, Info, ShieldAlert, Sparkles, TrendingUp, X } from 'lucide-react';
import { useScreening } from '../../context/ScreeningContext';

export const SecurityDetailDrawer = () => {
  const { selectedSecurity, setSelectedSecurityId, setSecurityDecision } = useScreening();

  const [localReason, setLocalReason] = useState('');
  const [localNote, setLocalNote] = useState('');

  useEffect(() => {
    if (selectedSecurity) {
      setLocalReason(selectedSecurity.decisionReason || '');
      setLocalNote(selectedSecurity.decisionNote || '');
    }
  }, [selectedSecurity]);

  if (!selectedSecurity) return null;

  const handleDecision = (decisionType) => {
    setSecurityDecision(selectedSecurity.id, decisionType, localReason, localNote);
  };

  const handleReasonChange = (val) => {
    setLocalReason(val);
    if (selectedSecurity.decision) {
      setSecurityDecision(selectedSecurity.id, selectedSecurity.decision, val, localNote);
    }
  };

  const handleNoteChange = (val) => {
    setLocalNote(val);
    if (selectedSecurity.decision) {
      setSecurityDecision(selectedSecurity.id, selectedSecurity.decision, localReason, val);
    }
  };

  const isExited = selectedSecurity.deltaStatus === 'exited' || selectedSecurity.rankDelta === 'EXITED';
  const isNew = selectedSecurity.deltaStatus === 'entered' || selectedSecurity.rankDelta === 'NEW';
  const isMover = selectedSecurity.deltaStatus === 'moved_up' || selectedSecurity.deltaStatus === 'moved_down';

  return (
    <div className="w-[450px] bg-white border-l border-slate-200/90 shadow-xl flex flex-col h-full shrink-0 z-20 overflow-y-auto">
      {/* Header */}
      <div className="p-6 border-b border-slate-100 flex items-start justify-between bg-slate-50/50">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-serif font-bold text-slate-900 leading-snug">
              {selectedSecurity.name}
            </h2>
            {isNew && (
              <span className="rounded bg-amber-100 border border-amber-300 px-1.5 py-0.5 text-[10px] font-bold text-amber-900">
                ★ NEW
              </span>
            )}
            {isExited && (
              <span className="rounded bg-rose-100 border border-rose-300 px-1.5 py-0.5 text-[10px] font-bold text-rose-800">
                EXITED
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            {selectedSecurity.ticker} · {selectedSecurity.sector} · {selectedSecurity.country} · {selectedSecurity.marketCapCategory || 'Large Cap'}
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="text-right">
            <span className="block text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
              Score
            </span>
            <div className="flex items-baseline justify-end gap-1">
              <span className="text-2xl font-bold font-serif text-slate-900 leading-none">
                {selectedSecurity.score}
              </span>
              {selectedSecurity.prevScore !== undefined && selectedSecurity.prevScore !== null && selectedSecurity.score !== selectedSecurity.prevScore && (
                <span className={`text-xs font-bold ${selectedSecurity.score > selectedSecurity.prevScore ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {selectedSecurity.score > selectedSecurity.prevScore ? `+${selectedSecurity.score - selectedSecurity.prevScore}` : selectedSecurity.score - selectedSecurity.prevScore}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={() => setSelectedSecurityId(null)}
            className="text-slate-400 hover:text-slate-700 p-1 text-base transition-colors rounded hover:bg-slate-200/50 cursor-pointer"
            title="Close Drawer"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* 1. Before vs After Rule Comparison & Attribution Card */}
        {selectedSecurity.ruleComparison && (
          <div
            className={`rounded-lg border p-4 text-xs space-y-2.5 shadow-2xs ${
              isExited
                ? 'border-rose-200 bg-rose-50/50 text-rose-950'
                : isNew
                ? 'border-emerald-200 bg-emerald-50/50 text-emerald-950'
                : 'border-teal-200 bg-teal-50/40 text-teal-950'
            }`}
          >
            <div className="flex items-center justify-between border-b border-black/10 pb-2">
              <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[10px]">
                {isExited ? (
                  <>
                    <ShieldAlert size={14} className="text-rose-600" />
                    <span className="text-rose-800">Exited Top 20: Rule Impact</span>
                  </>
                ) : isNew ? (
                  <>
                    <Sparkles size={14} className="text-emerald-600" />
                    <span className="text-emerald-800">New Entrant: Market Impact</span>
                  </>
                ) : (
                  <>
                    <TrendingUp size={14} className="text-[#147b73]" />
                    <span className="text-[#147b73]">Score & Rank Delta</span>
                  </>
                )}
              </div>
              <span className="text-[10px] font-semibold opacity-75">Run #5 vs Run #4</span>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-baseline font-medium text-[11px]">
                <span className="text-slate-600">Metric Trigger:</span>
                <span className="font-bold text-slate-900">{selectedSecurity.ruleComparison.metric}</span>
              </div>
              {selectedSecurity.ruleComparison.stockValue && (
                <div className="flex justify-between items-baseline font-medium text-[11px]">
                  <span className="text-slate-600">Stock Actual Value:</span>
                  <span className="font-mono font-bold text-slate-800">{selectedSecurity.ruleComparison.stockValue}</span>
                </div>
              )}
              {selectedSecurity.ruleComparison.oldRule && (
                <div className="flex justify-between items-baseline font-medium text-[11px]">
                  <span className="text-slate-600">Run #4 Rule (v1.0):</span>
                  <span className="font-mono text-slate-700">{selectedSecurity.ruleComparison.oldRule}</span>
                </div>
              )}
              {selectedSecurity.ruleComparison.newRule && (
                <div className="flex justify-between items-baseline font-medium text-[11px]">
                  <span className="text-slate-600">Run #5 Rule (v2.0):</span>
                  <span className="font-mono font-bold text-slate-900">{selectedSecurity.ruleComparison.newRule}</span>
                </div>
              )}
            </div>

            <p className="text-[11px] leading-relaxed pt-1 border-t border-black/10 font-medium">
              {selectedSecurity.ruleComparison.explanation}
            </p>
          </div>
        )}

        {/* 2. Score Breakdown Section */}
        <div>
          <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center justify-between">
            <span>Score Breakdown</span>
            <span className="text-[10px] font-medium text-slate-400">Total: {selectedSecurity.score}/100</span>
          </h3>
          <div className="space-y-4">
            {selectedSecurity.scoreBreakdown && selectedSecurity.scoreBreakdown.length > 0 ? (
              selectedSecurity.scoreBreakdown.map((metric, idx) => {
                const isExempt = metric.status === 'exempt';
                const isMiss = metric.status === 'miss';
                const isThreshold = metric.status === 'threshold';

                return (
                  <div key={idx} className="space-y-1.5 rounded-md border border-slate-100 bg-slate-50/50 p-2.5">
                    <div className="flex justify-between items-baseline text-xs">
                      <span className="font-semibold text-slate-800">{metric.name}</span>
                      <span className="font-mono text-slate-700 font-semibold text-[11px]">
                        {isExempt ? (
                          <span className="text-[#147b73] font-bold">Bank Exempt</span>
                        ) : (
                          `${metric.score} / ${metric.maxScore} pts`
                        )}
                      </span>
                    </div>

                    {/* Progress Meter */}
                    {!isExempt && (
                      <div className="w-full bg-slate-200/80 h-2 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            isMiss
                              ? 'bg-rose-500'
                              : isThreshold
                              ? 'bg-amber-500'
                              : 'bg-[#147b73]'
                          }`}
                          style={{ width: `${Math.min(100, Math.max(5, metric.percentage))}%` }}
                        />
                      </div>
                    )}

                    <div className="flex justify-between text-[11px] text-slate-500 pt-0.5">
                      <span>Actual: <strong className="text-slate-700">{metric.valueDisplay}</strong></span>
                      <span>Target: <strong className="text-slate-700">{metric.benchmarkDisplay}</strong></span>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-slate-400">Detailed metric breakdown unavailable.</p>
            )}
          </div>
        </div>

        {/* 3. Rank History (Last 6 Runs) */}
        <div>
          <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2.5">
            Rank History (Last 6 Runs)
          </h3>
          <div className="rounded-md border border-slate-200 bg-slate-50/60 p-3 text-xs font-mono text-slate-700 flex items-center space-x-2 flex-wrap">
            {selectedSecurity.rankHistory && selectedSecurity.rankHistory.length > 0 ? (
              selectedSecurity.rankHistory.map((rnk, i) => {
                const isLast = i === selectedSecurity.rankHistory.length - 1;
                return (
                  <React.Fragment key={i}>
                    <span
                      className={`px-2 py-0.5 rounded ${
                        isLast
                          ? rnk === 'EXIT'
                            ? 'bg-rose-100 text-rose-800 font-bold border border-rose-200'
                            : 'bg-teal-100 text-[#147b73] font-bold border border-teal-200'
                          : 'bg-white border border-slate-200 text-slate-600'
                      }`}
                    >
                      {rnk}
                    </span>
                    {!isLast && <span className="text-slate-300">→</span>}
                  </React.Fragment>
                );
              })
            ) : (
              <span>#1</span>
            )}
          </div>
        </div>

        {/* 4. Data Sources & Confidence */}
        <div>
          <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2.5">
            Data Sources &amp; Confidence
          </h3>
          <div className="bg-[#fcfdfd] border border-slate-200/80 rounded-lg p-3.5 space-y-2 text-xs">
            <div className="flex items-start justify-between gap-2">
              <span className="text-slate-700 font-medium leading-relaxed">
                {selectedSecurity.confidenceDetails?.estimateNote || 'Consensus estimates verified across financial feeds'}
              </span>
              <span className="shrink-0 px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold rounded">
                High Confidence
              </span>
            </div>
            <div className="text-[11px] text-slate-400">
              {selectedSecurity.confidenceDetails?.freshnessNote || 'Fundamentals refreshed for current quarter'}
            </div>
          </div>
        </div>

        {/* 5. Analyst Decision */}
        <div>
          <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2.5">
            Your Decision
          </h3>
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => handleDecision('keep')}
                className={`px-5 py-2 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                  selectedSecurity.decision === 'keep'
                    ? 'bg-[#147b73] text-white shadow-xs'
                    : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
                }`}
              >
                Keep
              </button>
              <button
                type="button"
                onClick={() => handleDecision('drop')}
                className={`px-5 py-2 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                  selectedSecurity.decision === 'drop'
                    ? 'bg-rose-600 text-white shadow-xs'
                    : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
                }`}
              >
                Drop
              </button>
              <div className="flex-1">
                <select
                  value={localReason}
                  onChange={(e) => handleReasonChange(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-md px-3 py-2 text-xs text-slate-700 focus:outline-hidden focus:border-[#147b73]"
                >
                  <option value="">Reason for decision (optional)</option>
                  <option value="valuation_headroom">Valuation headroom</option>
                  <option value="earnings_quality">High earnings quality</option>
                  <option value="regulatory_risk">Regulatory overhang</option>
                  <option value="debt_profile">Elevated leverage</option>
                  <option value="cyclical_exposure">High cyclical exposure</option>
                </select>
              </div>
            </div>

            {/* Note text field */}
            <div>
              <input
                type="text"
                placeholder="Add an analyst note (optional)"
                value={localNote}
                onChange={(e) => handleNoteChange(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-md px-3 py-2 text-xs text-slate-700 placeholder-slate-400 focus:outline-hidden focus:border-[#147b73]"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
