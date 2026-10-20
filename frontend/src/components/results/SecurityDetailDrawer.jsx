
import React, { useState, useEffect } from 'react';
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

  return (
    <div className="w-[430px] bg-white border-l border-slate-200/90 shadow-xl flex flex-col h-full shrink-0 z-20 overflow-y-auto">
      {/* Header */}
      <div className="p-6 border-b border-slate-100 flex items-start justify-between">
        <div>
          <h2 className="text-xl font-serif font-bold text-slate-900 leading-snug">
            {selectedSecurity.name}
          </h2>
          <p className="text-xs text-slate-400 mt-1 font-medium">
            {selectedSecurity.ticker} · {selectedSecurity.sector} · {selectedSecurity.country} · {selectedSecurity.marketCapCategory}
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="text-right">
            <span className="block text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
              Score
            </span>
            <span className="text-2xl font-bold font-serif text-slate-900 leading-none">
              {selectedSecurity.score}
            </span>
          </div>
          <button
            onClick={() => setSelectedSecurityId(null)}
            className="text-slate-400 hover:text-slate-700 p-1 text-base transition-colors"
            title="Close Drawer"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="p-6 space-y-7">
        {/* Score Breakdown Section */}
        <div>
          <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-4">
            Score Breakdown
          </h3>
          <div className="space-y-4">
            {selectedSecurity.scoreBreakdown && selectedSecurity.scoreBreakdown.length > 0 ? (
              selectedSecurity.scoreBreakdown.map((metric, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between items-baseline text-xs">
                    <span className="font-semibold text-slate-800">{metric.name}</span>
                    <span className="font-mono text-slate-600 font-medium">
                      {metric.score} / {metric.maxScore}
                    </span>
                  </div>

                  {/* Progress Meter */}
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-[#146b63] h-full rounded-full transition-all"
                      style={{ width: `${metric.percentage}%` }}
                    />
                  </div>

                  <div className="flex justify-between text-[11px] text-slate-400">
                    <span>{metric.valueDisplay}</span>
                    <span>{metric.benchmarkDisplay}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400">Detailed metric breakdown unavailable.</p>
            )}
          </div>
        </div>

        {/* Data Sources & Confidence */}
        <div>
          <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-3">
            Data Sources & Confidence
          </h3>
          <div className="bg-[#fcfdfd] border border-slate-200/80 rounded-lg p-3.5 space-y-2 text-xs">
            <div className="flex items-start justify-between gap-2">
              <span className="text-slate-700 font-medium leading-relaxed">
                {selectedSecurity.confidenceDetails?.estimateNote || 'Estimates consensus aligned'}
              </span>
              <span className="shrink-0 px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-semibold rounded">
                4% apart
              </span>
            </div>
            <div className="text-[11px] text-slate-400">
              {selectedSecurity.confidenceDetails?.freshnessNote || 'Fundamentals refreshed for current quarter'}
            </div>
          </div>
        </div>

        {/* Your Decision */}
        <div>
          <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-3">
            Your Decision
          </h3>
          <div className="space-y-3">
            {/* Decision Buttons */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleDecision('keep')}
                className={`px-5 py-2 text-xs font-semibold rounded-md transition-colors ${
                  selectedSecurity.decision === 'keep'
                    ? 'bg-[#146b63] text-white shadow-xs'
                    : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
                }`}
              >
                Keep
              </button>
              <button
                onClick={() => handleDecision('drop')}
                className={`px-5 py-2 text-xs font-semibold rounded-md transition-colors ${
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
                  className="w-full bg-white border border-slate-300 rounded-md px-3 py-2 text-xs text-slate-700 focus:outline-hidden focus:border-[#146b63]"
                >
                  <option value="">Reason: choose from list ▾</option>
                  <option value="Yield & valuation cushion">Yield & valuation cushion</option>
                  <option value="Strong cash flow profile">Strong cash flow profile</option>
                  <option value="Risk/reward asymmetric">Risk/reward asymmetric</option>
                  <option value="Sector overconcentration">Sector overconcentration</option>
                  <option value="High leverage threshold risk">High leverage threshold risk</option>
                </select>
              </div>
            </div>

            {/* Note text field */}
            <div>
              <input
                type="text"
                placeholder="Add a note (optional)"
                value={localNote}
                onChange={(e) => handleNoteChange(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-md px-3 py-2 text-xs text-slate-700 placeholder-slate-400 focus:outline-hidden focus:border-[#146b63]"
              />
            </div>
          </div>
        </div>

        {/* Rank History */}
        <div>
          <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
            Rank History (Last 6 Runs)
          </h3>
          <div className="text-xs font-mono text-slate-600 flex items-center space-x-1.5 flex-wrap">
            {selectedSecurity.rankHistory && selectedSecurity.rankHistory.length > 0 ? (
              selectedSecurity.rankHistory.map((rnk, i) => (
                <React.Fragment key={i}>
                  <span className={i === selectedSecurity.rankHistory.length - 1 ? 'font-bold text-[#146b63]' : ''}>
                    {rnk}
                  </span>
                  {i < selectedSecurity.rankHistory.length - 1 && <span className="text-slate-300">→</span>}
                </React.Fragment>
              ))
            ) : (
              <span>#1</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
