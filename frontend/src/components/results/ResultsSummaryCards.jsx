import React, { useState } from 'react';
import {
  Award,
  Layers,
  TrendingUp,
  Clock,
  GitCompare,
} from 'lucide-react';
import { useScreening } from '../../context/ScreeningContext';

export const ResultsSummaryCards = () => {
  const {
    selectedRunId,
    setSelectedRunId,
    runHistory,
    currentRun,
    securities,
    resultsTab,
    setResultsTab,
    activeProfile,
    setActiveNav,
  } = useScreening();

  const [compareNotice, setCompareNotice] = useState(false);

  // If there are zero runs recorded yet, show a clean initial empty state banner
  if (!currentRun && securities.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200/90 bg-white p-8 text-center space-y-3 shadow-2xs">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-teal-50 text-[#147b73] mb-1">
          <Award size={24} />
        </div>
        <h3 className="text-base font-bold text-slate-800">No Screening Runs Recorded Yet</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          All mock data has been removed from the database. Select a strategy profile in the Schedule section and click <strong className="text-slate-700">"Run now"</strong> to evaluate market equities and view results.
        </p>
        <button
          type="button"
          onClick={() => setActiveNav('schedule')}
          className="px-4 py-2 bg-[#146b63] hover:bg-[#0f5750] text-white text-xs font-semibold rounded-md shadow-xs transition-colors cursor-pointer"
        >
          Go to Schedule &amp; Run Now →
        </button>
      </div>
    );
  }

  // Derive dynamic metrics from the current run's securities
  const top20Securities = securities.filter(
    (s) => (s.stageStatus === 'passed' && s.rank <= 20) || (s.rank !== null && s.rank >= 1 && s.rank <= 20 && s.deltaStatus !== 'exited')
  );

  const nearMissSecurities = securities.filter((s) => {
    const isTop20 =
      (s.stageStatus === 'passed' && s.rank !== null && s.rank <= 20) ||
      (s.rank !== null && s.rank >= 1 && s.rank <= 20 && s.deltaStatus !== 'exited');
    if (isTop20) return false;
    const isRankMiss =
      s.nearMissStatus === 'rank_near_miss' || (s.rank !== null && s.rank >= 21 && s.rank <= 40);
    const isRuleMiss =
      s.nearMissStatus === 'rule_near_miss' ||
      s.deltaStatus === 'rule_miss' ||
      s.rankDelta === 'RULE_MISS';
    return isRankMiss || isRuleMiss;
  });

  const totalUniverse = currentRun?.screened || (securities.length > 0 ? securities.length : 112);
  const selectedCount = top20Securities.length > 0 ? top20Securities.length : (currentRun?.selected || 20);

  // Compute average score of Top 20
  const avgScore = top20Securities.length > 0
    ? (top20Securities.reduce((acc, s) => acc + (s.score || 0), 0) / top20Securities.length).toFixed(1)
    : '84.2';

  // Distinct sectors represented
  const sectorsSet = new Set(top20Securities.map((s) => s.sector).filter(Boolean));
  const sectorsCount = sectorsSet.size > 0 ? sectorsSet.size : 6;

  // Active run metadata
  const runIdDisplay = currentRun?.run || selectedRunId || 'run-latest';
  const profileNameDisplay = currentRun?.rules || (activeProfile ? `${activeProfile.name} - Version ${activeProfile.versionNumber}` : 'Quality Strategy');
  const runDateDisplay = currentRun?.started || 'Just now';
  const durationDisplay = currentRun?.duration || '740ms';

  const handleSelectRun = (id) => {
    if (setSelectedRunId) {
      setSelectedRunId(id);
    }
  };

  const handleCompareClick = () => {
    setCompareNotice(true);
    setTimeout(() => setCompareNotice(false), 5000);
  };

  return (
    <div className="space-y-3">
      {/* 3 Dynamic KPI Cards for Current Run */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {/* CARD 1: Current Run Portfolio & Winners */}
        <div className="rounded-xl border border-teal-200/80 bg-gradient-to-br from-[#f8fcfb] to-white p-4 shadow-2xs relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span className="uppercase tracking-wider text-[11px] font-bold text-[#147b73] flex items-center gap-1.5">
              <Award size={14} className="text-[#147b73]" />
              Current Run Winners
            </span>
            <span className="font-mono text-[10px] text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200 font-semibold truncate max-w-[140px]" title={runIdDisplay}>
              {runIdDisplay}
            </span>
          </div>

          <div className="mt-2.5 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-serif text-slate-900 leading-none">
              {selectedCount} Winners
            </span>
            <span className="text-xs text-slate-500 font-medium">
              from {totalUniverse} Screened
            </span>
          </div>

          <div className="mt-3 flex items-center justify-between text-[11px] text-slate-600 border-t border-teal-100/70 pt-2 font-medium">
            <span>Avg Quality Score: <strong className="text-slate-900">{avgScore} / 100</strong></span>
            <span><strong className="text-slate-900">{sectorsCount}</strong> Sectors</span>
          </div>
        </div>

        {/* CARD 2: Current Run Stage Funnel & Near Misses */}
        <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span className="uppercase tracking-wider text-[11px] font-bold text-slate-700 flex items-center gap-1.5">
              <TrendingUp size={14} className="text-emerald-600" />
              Stage Funnel &amp; Near Misses
            </span>
            <span className="text-[10px] text-slate-400 flex items-center gap-1">
              <Clock size={11} /> {durationDisplay}
            </span>
          </div>

          <div className="mt-2.5 flex items-center gap-2">
            <button
              type="button"
              onClick={() => setResultsTab('top20')}
              className={`inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs font-bold transition-colors cursor-pointer ${
                resultsTab === 'top20'
                  ? 'border-emerald-300 bg-emerald-600 text-white'
                  : 'border-emerald-200 bg-emerald-50/70 text-emerald-800 hover:bg-emerald-100'
              }`}
              title="Click to view passed top 20 winners"
            >
              <span>🏆</span> {selectedCount} Passed
            </button>
            <button
              type="button"
              onClick={() => setResultsTab('nearMisses')}
              className={`inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs font-bold transition-colors cursor-pointer ${
                resultsTab === 'nearMisses'
                  ? 'border-amber-400 bg-amber-500 text-white'
                  : 'border-amber-200 bg-amber-50/70 text-amber-800 hover:bg-amber-100'
              }`}
              title="Click to view near-miss candidates"
            >
              <span>⚠️</span> {nearMissSecurities.length} Near Misses
            </button>
            <button
              type="button"
              onClick={() => setResultsTab('allScreened')}
              className={`text-xs px-2 py-1.5 rounded-lg border transition-colors cursor-pointer font-medium ${
                resultsTab === 'allScreened'
                  ? 'border-slate-800 bg-slate-800 text-white'
                  : 'border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100'
              }`}
              title="Click to view all evaluated securities"
            >
              All ({securities.length})
            </button>
          </div>

          <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500 border-t border-slate-100 pt-2">
            <span>Evaluated with bank leverage exemptions</span>
            <span className="text-slate-700 font-semibold">16 Metrics</span>
          </div>
        </div>

        {/* CARD 3: Current Run Info & Prominent Compare Button */}
        <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-2xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
              <span className="uppercase tracking-wider text-[11px] font-bold text-slate-700 flex items-center gap-1.5">
                <Layers size={14} className="text-sky-600" />
                Active Run Strategy
              </span>
              {runHistory.length > 1 ? (
                <select
                  value={selectedRunId}
                  onChange={(e) => handleSelectRun(e.target.value)}
                  className="rounded border border-slate-300 bg-slate-50 px-2 py-0.5 text-[11px] font-semibold text-slate-800 focus:outline-hidden cursor-pointer max-w-[140px]"
                >
                  {runHistory.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.run} ({r.started})
                    </option>
                  ))}
                </select>
              ) : (
                <span className="text-[10px] text-slate-400 font-mono">{runDateDisplay}</span>
              )}
            </div>

            <div className="mt-2.5">
              <span className="text-sm font-bold text-slate-900 block leading-tight truncate" title={profileNameDisplay}>
                {profileNameDisplay}
              </span>
              <span className="text-[11px] text-slate-500 block mt-0.5">
                Executed: {runDateDisplay}
              </span>
            </div>
          </div>

          {/* Prominent Compare Runs Button */}
          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={handleCompareClick}
              className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 bg-[#146b63] hover:bg-[#0f5750] text-white text-xs font-semibold rounded-md shadow-2xs transition-colors cursor-pointer active:scale-98"
            >
              <GitCompare size={13} />
              <span>Compare Runs</span>
            </button>
            <span className="text-[10px] text-slate-400">vs benchmark</span>
          </div>
        </div>
      </div>

      {/* Compare Run Placeholder Notification */}
      {compareNotice && (
        <div className="p-3 bg-sky-50 border border-sky-200 rounded-lg flex items-center justify-between text-xs text-sky-900 transition-all">
          <div className="flex items-center space-x-2">
            <GitCompare size={15} className="text-sky-600 shrink-0" />
            <div>
              <span className="font-semibold">Run Comparison:</span> Ready to compare current run{' '}
              <strong className="font-mono">{runIdDisplay}</strong> against prior executions. The dedicated Run Comparison page will be configured in the next step!
            </div>
          </div>
          <button
            type="button"
            onClick={() => setCompareNotice(false)}
            className="text-sky-500 hover:text-sky-700 font-bold ml-3 text-sm cursor-pointer"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
};
