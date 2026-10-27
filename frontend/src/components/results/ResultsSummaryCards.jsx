import React, { useState } from 'react';
import {
  Award,
  ChevronDown,
  ChevronUp,
  Layers,
  Sparkles,
  TrendingUp,
  Zap,
  ArrowRight,
  ShieldAlert,
  Sliders,
  CheckCircle2,
} from 'lucide-react';
import { useScreening } from '../../context/ScreeningContext';
import { MOCK_RUNS_DATA } from '../../data/mockData';

export const ResultsSummaryCards = () => {
  const {
    selectedRunId,
    setSelectedRunId,
    compareRunId,
    setCompareRunId,
    runHistory,
    setResultsTab,
    setChangesSubTab,
  } = useScreening();

  const [isDiffExpanded, setIsDiffExpanded] = useState(false);

  const activeRunId = selectedRunId || 'run-005';
  const runMeta = MOCK_RUNS_DATA[activeRunId] || MOCK_RUNS_DATA['run-005'];
  const activeCompareId = compareRunId !== undefined ? compareRunId : 'run-004';
  const comparisonMeta = activeCompareId !== 'none' ? MOCK_RUNS_DATA[activeCompareId] : null;

  const handleSelectRun = (id) => {
    if (setSelectedRunId) setSelectedRunId(id);
  };

  const handleSelectCompare = (id) => {
    if (setCompareRunId) setCompareRunId(id);
  };

  const handleFilterEntered = () => {
    if (setResultsTab) setResultsTab('changes');
    if (setChangesSubTab) setChangesSubTab('entered');
  };

  const handleFilterExited = () => {
    if (setResultsTab) setResultsTab('changes');
    if (setChangesSubTab) setChangesSubTab('exited');
  };

  const enteredCount = runMeta.summary.turnover.entered;
  const exitedCount = runMeta.summary.turnover.exited;
  const retainedCount = runMeta.summary.turnover.retained;

  return (
    <div className="space-y-3">
      {/* 3 User-Friendly KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {/* CARD 1: Top 20 Selected */}
        <div className="rounded-xl border border-teal-200/80 bg-gradient-to-br from-[#f8fcfb] to-white p-4 shadow-2xs relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span className="uppercase tracking-wider text-[11px] font-bold text-[#147b73] flex items-center gap-1.5">
              <Award size={14} className="text-[#147b73]" />
              Selected Portfolio
            </span>
            <span className="font-mono text-[11px] text-slate-400">
              {runMeta.date}
            </span>
          </div>

          <div className="mt-2.5 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-serif text-slate-900 leading-none">
              {runMeta.summary.selectedCount} Winners
            </span>
            <span className="text-xs text-slate-500 font-medium">
              from {runMeta.summary.totalUniverse.toLocaleString()} Universe
            </span>
          </div>

          <div className="mt-3 flex items-center justify-between text-[11px] text-slate-600 border-t border-teal-100/70 pt-2 font-medium">
            <span>Avg Quality Score: <strong className="text-slate-900">{runMeta.summary.avgScore} / 100</strong></span>
            <span><strong className="text-slate-900">{runMeta.summary.sectorsRepresented}</strong> Sectors</span>
          </div>
        </div>

        {/* CARD 2: Turnover (Since Last Run) with Instant Filter Buttons */}
        <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span className="uppercase tracking-wider text-[11px] font-bold text-slate-700 flex items-center gap-1.5">
              <TrendingUp size={14} className="text-emerald-600" />
              Turnover &amp; Movement
            </span>
            <span className="text-[10px] text-slate-400">vs Previous Run</span>
          </div>

          <div className="mt-2.5 flex items-center gap-2">
            <button
              type="button"
              onClick={handleFilterEntered}
              className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50/70 px-3 py-1.5 text-xs font-bold text-emerald-800 hover:bg-emerald-100 transition-colors cursor-pointer"
              title="Click to view entered stocks"
            >
              <span>▲</span> {enteredCount} Entered
            </button>
            <button
              type="button"
              onClick={handleFilterExited}
              className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50/70 px-3 py-1.5 text-xs font-bold text-rose-800 hover:bg-rose-100 transition-colors cursor-pointer"
              title="Click to view exited stocks"
            >
              <span>▼</span> {exitedCount} Exited
            </button>
            <span className="text-xs text-slate-500 font-medium ml-1">
              {retainedCount} Retained
            </span>
          </div>

          <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500 border-t border-slate-100 pt-2">
            <span className="italic">Click badges above to filter table instantly</span>
            <span className="text-emerald-700 font-semibold">{retainedCount > 0 ? `${Math.round((retainedCount/20)*100)}% stability` : ''}</span>
          </div>
        </div>

        {/* CARD 3: Run Selector & Strategy Comparison */}
        <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span className="uppercase tracking-wider text-[11px] font-bold text-slate-700 flex items-center gap-1.5">
              <Layers size={14} className="text-sky-600" />
              Viewing Strategy
            </span>
            <select
              value={activeRunId}
              onChange={(e) => handleSelectRun(e.target.value)}
              className="rounded border border-slate-300 bg-slate-50 px-2 py-0.5 text-[11px] font-semibold text-slate-800 focus:outline-hidden cursor-pointer"
            >
              <option value="run-005">Run #5 (Today)</option>
              <option value="run-004">Run #4 (Yesterday)</option>
              <option value="run-003">Run #3 (24 Oct)</option>
            </select>
          </div>

          <div className="mt-2.5 flex items-baseline justify-between">
            <div>
              <span className="text-base font-bold text-slate-900 block leading-tight">
                {runMeta.profileName}
              </span>
              <span className="text-[11px] text-slate-500">
                Compare with:{' '}
                <select
                  value={activeCompareId}
                  onChange={(e) => handleSelectCompare(e.target.value)}
                  className="rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[11px] font-medium text-slate-700 focus:outline-hidden cursor-pointer ml-1"
                >
                  <option value="none">None</option>
                  <option value="run-004">Run #4 (v1.0)</option>
                  <option value="run-003">Run #3 (v1.0)</option>
                </select>
              </span>
            </div>

            {comparisonMeta && runMeta.ruleDiffs?.length > 0 && (
              <button
                type="button"
                onClick={() => setIsDiffExpanded((prev) => !prev)}
                className="inline-flex items-center gap-1 rounded border border-teal-200 bg-[#f0f9f8] px-2 py-1 text-[10px] font-bold text-[#147b73] hover:bg-teal-100 transition-colors cursor-pointer shrink-0"
              >
                <span>{runMeta.ruleDiffs.length} Diffs</span>
                {isDiffExpanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
              </button>
            )}
          </div>

          <div className="mt-2.5 border-t border-slate-100 pt-2 text-[11px] text-slate-600 truncate font-medium">
            {runMeta.impactSummary || 'Baseline strategy execution'}
          </div>
        </div>
      </div>

      {/* Collapsible Rule Differences Drawer (Shown when user clicks "Diffs") */}
      {isDiffExpanded && comparisonMeta && runMeta.ruleDiffs?.length > 0 && (
        <div className="rounded-xl border border-teal-200 bg-[#f4faf9] p-4 text-xs shadow-2xs space-y-2.5">
          <div className="flex items-center justify-between border-b border-teal-100 pb-2">
            <div className="flex items-center gap-2">
              <span className="rounded bg-[#147b73] px-2 py-0.5 text-[10px] font-bold text-white uppercase tracking-wider">
                Rule Diffs
              </span>
              <span className="font-semibold text-slate-800">
                Modifications between {runMeta.title} and {comparisonMeta.title}:
              </span>
            </div>
            <button
              type="button"
              onClick={() => setIsDiffExpanded(false)}
              className="text-slate-400 hover:text-slate-700 text-xs font-semibold cursor-pointer"
            >
              ✕ Close
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {runMeta.ruleDiffs.map((diff, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1.5 rounded-full border border-slate-200/80 bg-white px-3 py-1 text-[11px] font-medium text-slate-800 shadow-2xs"
              >
                <span className="font-bold text-[#147b73]">{diff.type}:</span>
                <span>{diff.text}</span>
              </span>
            ))}
          </div>

          <p className="text-[11px] text-slate-600 font-medium pt-1">
            <strong>Cause &amp; Effect:</strong> {runMeta.impactSummary}
          </p>
        </div>
      )}
    </div>
  );
};

