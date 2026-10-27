import React from 'react';
import { useScreening } from '../../context/ScreeningContext';

export const ResultsTable = ({ holdings, uploadedHoldingRows }) => {
  const {
    securities,
    selectedSecurity,
    setSelectedSecurityId,
    setSecurityDecision,
    filterSector,
    filterRegion,
    filterCap,
    searchQuery,
    resultsTab,
    changesSubTab,
    nearMissSubTab,
  } = useScreening();

  const countryValueByResultCountry = {
    US: 'United States',
    IN: 'India',
    UK: 'United Kingdom',
    DE: 'Germany',
    FR: 'France',
    CH: 'Switzerland',
    NL: 'Netherlands',
    NO: 'Norway',
    TW: 'Taiwan',
    IT: 'Italy',
    ES: 'Spain',
  };

  // Filter securities by primary tab and sub-pills
  const tabSecurities = React.useMemo(() => {
    if (resultsTab === 'myHoldings') {
      return holdings || [];
    }

    if (resultsTab === 'changes') {
      return securities.filter((s) => {
        const isEntered = s.deltaStatus === 'entered' || s.rankDelta === 'NEW';
        const isExited = s.deltaStatus === 'exited' || s.rankDelta === 'EXITED';
        if (changesSubTab === 'entered') return isEntered;
        if (changesSubTab === 'exited') return isExited;
        return isEntered || isExited;
      });
    }

    if (resultsTab === 'nearMisses') {
      return securities.filter((s) => {
        const isRankMiss = s.rank !== null && s.rank >= 21 && s.rank <= 40;
        const isRuleMiss =
          s.deltaStatus === 'rule_miss' ||
          s.rankDelta === 'RULE_MISS' ||
          Object.values(s.metricStatuses || {}).some(
            (status) => status === 'threshold' || status === 'miss'
          );
        if (nearMissSubTab === 'rank') return isRankMiss;
        if (nearMissSubTab === 'rule') return isRuleMiss;
        return isRankMiss || isRuleMiss;
      });
    }

    // Default: 'top20' (only actively qualified top 20 securities)
    return securities.filter(
      (s) => s.rank !== null && s.rank >= 1 && s.rank <= 20 && s.deltaStatus !== 'exited'
    );
  }, [resultsTab, changesSubTab, nearMissSubTab, securities, holdings]);

  // Secondary filters: sector, region, cap, and search query
  const filteredSecurities = React.useMemo(() => {
    return tabSecurities.filter((sec) => {
      if (filterSector && filterSector !== 'All' && sec.sector !== filterSector) {
        return false;
      }
      if (filterRegion && filterRegion !== 'All') {
        const resultCountry = countryValueByResultCountry[sec.country] || sec.country;
        if (resultCountry !== filterRegion) return false;
      }
      if (filterCap && filterCap !== 'All') {
        const cap = (sec.marketCapCategory || '').toLowerCase();
        if (filterCap === 'Large' && !cap.includes('large')) return false;
        if (filterCap === 'Mid' && !cap.includes('mid')) return false;
        if (filterCap === 'Small' && !cap.includes('small')) return false;
      }
      if (searchQuery && searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchName = sec.name?.toLowerCase().includes(q);
        const matchTicker = sec.ticker?.toLowerCase().includes(q);
        if (!matchName && !matchTicker) return false;
      }
      return true;
    });
  }, [tabSecurities, filterSector, filterRegion, filterCap, searchQuery]);

  // Empty states per tab
  const emptyStateByTab = {
    top20: {
      title: 'No Top 20 Securities Found',
      description: 'Adjust your sector, region, or search filters to view top qualifying companies.',
    },
    changes: {
      title: 'No Portfolio Turnover in This Run',
      description: 'No securities entered or exited between the selected runs.',
    },
    nearMisses: {
      title: 'No Near Misses Found',
      description: 'No securities fell immediately outside the cutoff rank or rule thresholds.',
    },
    myHoldings: {
      title: 'No Holdings Uploaded',
      description: 'Upload a CSV file containing your portfolio tickers to compare against screening results.',
    },
  };

  // Render My Holdings Table if user uploaded a file
  if (resultsTab === 'myHoldings' && uploadedHoldingRows && uploadedHoldingRows.length > 0) {
    const columns = Object.keys(uploadedHoldingRows[0]);
    return (
      <div className="overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-2xs">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200/80 bg-slate-50/70 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                {columns.map((column) => (
                  <th key={column} className="whitespace-nowrap px-3.5 py-3">{column}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {uploadedHoldingRows.map((row, rowIndex) => (
                <tr key={`holding-${rowIndex}`} className="hover:bg-slate-50/80 transition-colors">
                  {columns.map((column) => (
                    <td key={`${rowIndex}-${column}`} className="whitespace-nowrap px-3.5 py-3 text-slate-700 font-medium">
                      {row[column] || '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // Empty state rendering
  if (filteredSecurities.length === 0) {
    const emptyState = emptyStateByTab[resultsTab] || emptyStateByTab.top20;
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center shadow-2xs">
        <div className="text-2xl mb-2">🔍</div>
        <h3 className="text-sm font-bold text-slate-800">{emptyState.title}</h3>
        <p className="mx-auto mt-1 max-w-md text-xs leading-5 text-slate-500">
          {emptyState.description}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-3.5 w-12 text-center">#</th>
                <th className="py-3 px-3.5 min-w-[200px]">Security &amp; Ticker</th>
                <th className="py-3 px-3.5 whitespace-nowrap">Sector</th>
                <th className="py-3 px-3.5 whitespace-nowrap">Score</th>
                <th className="py-3 px-3.5 whitespace-nowrap">Movement</th>
                <th className="py-3 px-3.5 min-w-[220px]">Cause / Attribution</th>
                <th className="py-3 px-3.5 whitespace-nowrap">Key Valuation</th>
                <th className="py-3 px-3.5 text-center whitespace-nowrap">Decision</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredSecurities.map((item) => {
                const isSelected = selectedSecurity?.id === item.id;
                const isExited = item.deltaStatus === 'exited' || item.rankDelta === 'EXITED';
                const isNew = item.deltaStatus === 'entered' || item.rankDelta === 'NEW';
                const scoreDelta =
                  item.prevScore !== undefined && item.prevScore !== null
                    ? item.score - item.prevScore
                    : null;

                return (
                  <tr
                    key={item.id}
                    onClick={() => setSelectedSecurityId(item.id)}
                    className={`cursor-pointer transition-colors hover:bg-slate-50/90 ${
                      isSelected
                        ? 'bg-teal-50/60 border-l-4 border-[#147b73]'
                        : isExited
                        ? 'bg-rose-50/30'
                        : isNew
                        ? 'bg-amber-50/20'
                        : ''
                    }`}
                  >
                    {/* 1. Rank */}
                    <td className="py-3.5 px-3.5 text-center text-slate-500 font-mono text-[11px] whitespace-nowrap">
                      {item.rank !== null ? (
                        <span className="font-semibold text-slate-700">#{item.rank}</span>
                      ) : item.prevRank ? (
                        <span className="text-rose-500 line-through">#{item.prevRank}</span>
                      ) : (
                        '—'
                      )}
                    </td>

                    {/* 2. Security Name & Ticker */}
                    <td className="py-3.5 px-3.5">
                      <div className="font-bold text-slate-900 leading-snug">
                        {item.name}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-1.5 font-medium">
                        <span className="font-mono font-semibold text-slate-600">{item.ticker}</span>
                        <span>·</span>
                        <span>{item.country}</span>
                        {item.exchange && (
                          <>
                            <span>·</span>
                            <span className="text-slate-400">{item.exchange}</span>
                          </>
                        )}
                      </div>
                    </td>

                    {/* 3. Sector */}
                    <td className="py-3.5 px-3.5 text-slate-700 whitespace-nowrap font-medium">
                      <span className="inline-block rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-700">
                        {item.sector}
                      </span>
                    </td>

                    {/* 4. Score with Delta */}
                    <td className="py-3.5 px-3.5 whitespace-nowrap">
                      <div className="flex items-baseline gap-1.5">
                        <span className="text-sm font-bold text-slate-900 font-mono">
                          {item.score}
                        </span>
                        {scoreDelta !== null && scoreDelta !== 0 && (
                          <span
                            className={`text-[10px] font-bold font-mono px-1 py-0.2 rounded ${
                              scoreDelta > 0
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/60'
                                : 'bg-rose-50 text-rose-700 border border-rose-200/60'
                            }`}
                          >
                            {scoreDelta > 0 ? `+${scoreDelta}` : scoreDelta}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* 5. Movement / Status */}
                    <td className="py-3.5 px-3.5 whitespace-nowrap">
                      {isNew ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
                          ★ NEW
                        </span>
                      ) : isExited ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 border border-rose-200 px-2 py-0.5 text-[10px] font-bold text-rose-700">
                          ▼ EXITED
                        </span>
                      ) : item.rankDelta?.startsWith('+') ? (
                        <span className="inline-flex items-center gap-0.5 font-bold text-emerald-600 font-mono text-[11px]">
                          ▲ {item.rankDelta}
                        </span>
                      ) : item.rankDelta?.startsWith('-') ? (
                        <span className="inline-flex items-center gap-0.5 font-bold text-rose-600 font-mono text-[11px]">
                          ▼ {item.rankDelta}
                        </span>
                      ) : (
                        <span className="text-slate-400 text-[11px] font-mono">—</span>
                      )}
                    </td>

                    {/* 6. Cause / Attribution Badge */}
                    <td className="py-3.5 px-3.5">
                      <div className="text-[11px] font-medium" title={item.movementReason}>
                        {item.movementReason ? (
                          <span
                            className={`inline-block rounded-md px-2.5 py-1 text-[11px] font-medium leading-relaxed ${
                              isNew
                                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200/70'
                                : isExited
                                ? 'bg-rose-50 text-rose-800 border border-rose-200/70'
                                : 'bg-slate-50 text-slate-700 border border-slate-200/60'
                            }`}
                          >
                            {item.movementReason}
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </div>
                    </td>

                    {/* 7. Key Valuation (P/E & EV/EBITDA combined) */}
                    <td className="py-3.5 px-3.5 whitespace-nowrap">
                      <div className="font-mono text-slate-800 font-medium">
                        {item.fwdPe ? `${item.fwdPe}x P/E` : '—'}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {item.sector === 'Financials'
                          ? 'Bank Exempt'
                          : item.evEbitda > 0
                          ? `${item.evEbitda}x EV`
                          : 'n/a'}
                      </div>
                    </td>

                    {/* 8. Decision (Keep / Drop Action Buttons) */}
                    <td className="py-3.5 px-3.5 text-center whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                      <div className="inline-flex rounded-lg shadow-2xs space-x-1">
                        <button
                          type="button"
                          onClick={() => setSecurityDecision(item.id, 'keep')}
                          className={`px-2.5 py-1 text-[11px] font-bold rounded transition-colors cursor-pointer ${
                            item.decision === 'keep'
                              ? 'bg-[#147b73] text-white shadow-2xs'
                              : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
                          }`}
                        >
                          Keep
                        </button>
                        <button
                          type="button"
                          onClick={() => setSecurityDecision(item.id, 'drop')}
                          className={`px-2.5 py-1 text-[11px] font-bold rounded transition-colors cursor-pointer ${
                            item.decision === 'drop'
                              ? 'bg-rose-600 text-white shadow-2xs'
                              : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
                          }`}
                        >
                          Drop
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Helpful Hint */}
      <div className="flex items-center justify-between text-[11px] text-slate-500 px-1 py-1">
        <span>
          💡 <strong>Tip:</strong> Click any company row to inspect all 16 metrics, rule comparisons, and score breakdown in the right drawer.
        </span>
        <span className="font-medium text-slate-600">
          Showing {filteredSecurities.length} {filteredSecurities.length === 1 ? 'company' : 'companies'}
        </span>
      </div>
    </div>
  );
};
