import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Layers, RefreshCw, Zap, ArrowRight, CheckCircle2, AlertTriangle } from 'lucide-react';
import { useScreening } from '../../context/ScreeningContext';

export const RunComparisonHeader = () => {
  const {
    runHistory,
    selectedRunId,
    setSelectedRunId,
    compareRunId,
    setCompareRunId,
    funnelState,
    setFunnelState,
  } = useScreening();

  const [isDetailsOpen, setIsDetailsOpen] = useState(true);

  // Default to Run #5 and Run #4 if available
  const currentRun = (runHistory && runHistory.find((r) => r.id === selectedRunId)) || runHistory?.[0] || {
    id: 'run-005',
    run: '#5',
    rules: 'Tech Growth v2.0',
    started: 'Today, 09:30 AM',
    ruleChanges: [
      { type: 'Threshold', text: 'Forward P/E tightened to <= 20.0x (was <= 25.0x)' },
      { type: 'Market', text: '+ Added country: India (NSE / BSE)' },
      { type: 'Weight', text: 'EV/EBITDA weight increased to 25% (was 10%)' },
    ],
    impactSummary: '2 stocks knocked out by Forward P/E gate · 3 stocks entered from India · 1 stock displaced',
  };

  const comparisonRun = compareRunId !== 'none'
    ? runHistory?.find((r) => r.id === compareRunId) || {
        id: 'run-004',
        run: '#4',
        rules: 'Tech Growth v1.0',
        started: 'Yesterday, 09:30 AM',
      }
    : null;

  const handleSelectRun = (runId) => {
    if (setSelectedRunId) setSelectedRunId(runId);
    const targetRun = runHistory?.find((r) => r.id === runId);
    if (targetRun?.funnel && setFunnelState) {
      setFunnelState(targetRun.funnel);
    }
  };

  return (
    <div className="rounded-lg border border-slate-200/90 bg-white p-4 shadow-2xs space-y-3.5">
      {/* 1. Header Row: Run Selectors */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 font-semibold text-slate-700">
            <Layers size={14} className="text-[#147b73]" />
            <span>Viewing Run:</span>
          </div>
          <select
            value={selectedRunId || currentRun.id}
            onChange={(e) => handleSelectRun(e.target.value)}
            className="rounded-md border border-slate-300 bg-slate-50/80 px-2.5 py-1.5 text-xs font-semibold text-slate-800 focus:border-[#147b73] focus:outline-hidden cursor-pointer"
          >
            {runHistory && runHistory.length > 0 ? (
              runHistory.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.run} · {r.rules} ({r.started})
                </option>
              ))
            ) : (
              <option value="run-005">Run #5 · Tech Growth v2.0 (Today, 09:30 AM)</option>
            )}
          </select>

          <span className="text-slate-400 font-semibold mx-1">vs</span>

          <div className="flex items-center gap-1.5 text-slate-500 font-medium">
            <span>Compare with:</span>
          </div>
          <select
            value={compareRunId || 'run-004'}
            onChange={(e) => setCompareRunId && setCompareRunId(e.target.value)}
            className="rounded-md border border-slate-300 bg-slate-50/80 px-2.5 py-1.5 text-xs font-medium text-slate-700 focus:border-[#147b73] focus:outline-hidden cursor-pointer"
          >
            <option value="none">None (Single run view)</option>
            {runHistory &&
              runHistory
                .filter((r) => r.id !== (selectedRunId || currentRun.id))
                .map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.run} · {r.rules} ({r.started})
                  </option>
                ))}
          </select>
        </div>

        {compareRunId !== 'none' && (
          <button
            type="button"
            onClick={() => setIsDetailsOpen((prev) => !prev)}
            className="inline-flex items-center gap-1 rounded border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            {isDetailsOpen ? (
              <>
                <ChevronUp size={12} /> Hide rule diffs
              </>
            ) : (
              <>
                <ChevronDown size={12} /> Show rule diffs
              </>
            )}
          </button>
        )}
      </div>

      {/* 2. Collapsible Rule Modifications Banner (When comparison active) */}
      {compareRunId !== 'none' && isDetailsOpen && (
        <div className="rounded-md border border-teal-200/70 bg-[#f4faf9] p-3 text-xs space-y-2.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded bg-[#147b73] px-2 py-0.5 text-[10px] font-bold text-white uppercase tracking-wider">
                <Zap size={10} /> Rule Modifications
              </span>
              <span className="font-semibold text-slate-800">
                Differences from {comparisonRun ? `${comparisonRun.run} (${comparisonRun.rules})` : 'Previous Run'}:
              </span>
            </div>
            <span className="text-[11px] font-semibold text-[#147b73]">
              Cause &amp; Impact Attribution Active
            </span>
          </div>

          {/* Badges for modified rules */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-900 shadow-2xs">
              <span className="font-bold text-amber-700">Threshold:</span> Forward P/E &lt;= 20.0x (tightened from &lt;= 25.0x)
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-900 shadow-2xs">
              <span className="font-bold text-emerald-700">Market:</span> + Added Country: India (NSE / BSE)
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-[11px] font-semibold text-sky-900 shadow-2xs">
              <span className="font-bold text-sky-700">Weight:</span> EV/EBITDA weight increased to 25% (was 10%)
            </span>
          </div>

          {/* Bottom explanation line */}
          <div className="flex items-center gap-2 border-t border-teal-100/90 pt-2 text-[11px] text-slate-600">
            <AlertTriangle size={12} className="text-[#147b73] shrink-0" />
            <span className="font-medium">
              <strong className="text-slate-800">Direct Result Impact:</strong> 2 stocks knocked out by Forward P/E gate (e.g. MSFT 22.4x) · 3 stocks entered from India (TCS, HDFC, INFY) · 1 stock displaced (ADBE to #22).
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

