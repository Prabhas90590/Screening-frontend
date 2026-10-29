import React from 'react';
import { useScreening } from '../../context/ScreeningContext';

export const ResultsTable = ({
  holdings = [],
  buyCandidates = [],
  holdingTickerSet = new Set(),
  holdingsSubTab = 'all',
  uploadedHoldingRows = [],
}) => {
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
    currentRun,
    activeProfile,
  } = useScreening();

  const activeProfileName =
    currentRun?.rules ||
    (activeProfile ? activeProfile.name : 'Active Model');

  // ── DUAL HORIZONTAL SCROLLBAR SYNCHRONIZATION ──
  const topScrollRef = React.useRef(null);
  const tableScrollRef = React.useRef(null);
  const isSyncingTop = React.useRef(false);
  const isSyncingBottom = React.useRef(false);

  const [tableScrollWidth, setTableScrollWidth] = React.useState(0);
  const [hasHorizontalOverflow, setHasHorizontalOverflow] = React.useState(false);

  const updateScrollWidth = React.useCallback(() => {
    if (tableScrollRef.current) {
      const sw = tableScrollRef.current.scrollWidth;
      const cw = tableScrollRef.current.clientWidth;
      setTableScrollWidth(sw);
      setHasHorizontalOverflow(sw > cw + 1);
    }
  }, []);

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

  const enrichWithHoldings = React.useCallback(
    (list) => {
      return list.map((s) => {
        if (s.isHolding || s.isBuyCandidate) return s;
        const isHeld = holdingTickerSet?.has(s.ticker?.toUpperCase());
        const holdingMatch = isHeld
          ? (holdings || []).find((h) => h.ticker?.toUpperCase() === s.ticker?.toUpperCase())
          : null;
        const holdingRank = holdingMatch?.holdingRank ?? null;
        const currentRank = s.rank ?? null;
        const holdingRankDelta =
          currentRank !== null && holdingRank !== null ? holdingRank - currentRank : null;
        return {
          ...s,
          isHeld,
          holdingRank,
          holdingRankDelta,
          holdingWeight: holdingMatch?.weightPct,
        };
      });
    },
    [holdings, holdingTickerSet]
  );

  // Filter securities by primary tab and sub-pills
  const tabSecurities = React.useMemo(() => {
    if (resultsTab === 'myHoldings') {
      if (holdingsSubTab === 'top20') {
        return holdings.filter((h) => h.comparisonStatus === 'held_in_top20');
      }
      if (holdingsSubTab === 'exited') {
        return holdings.filter((h) => h.comparisonStatus === 'held_exited');
      }
      if (holdingsSubTab === 'unscreened') {
        return holdings.filter((h) => h.comparisonStatus === 'held_unscreened');
      }
      if (holdingsSubTab === 'buyIdeas') {
        return buyCandidates || [];
      }
      return holdings || [];
    }

    if (resultsTab === 'allScreened') {
      return enrichWithHoldings(securities);
    }

    if (resultsTab === 'changes') {
      const filtered = securities.filter((s) => {
        const isEntered = s.deltaStatus === 'entered' || s.rankDelta === 'NEW';
        const isExited = s.deltaStatus === 'exited' || s.rankDelta === 'EXITED';
        if (changesSubTab === 'entered') return isEntered;
        if (changesSubTab === 'exited') return isExited;
        return isEntered || isExited;
      });
      return enrichWithHoldings(filtered);
    }

    if (resultsTab === 'nearMisses') {
      const filtered = securities.filter((s) => {
        // Exclude Top 20 stocks completely - Top 20 winners must never appear under Near Misses
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

        if (nearMissSubTab === 'rank') return isRankMiss;
        if (nearMissSubTab === 'rule') return isRuleMiss && !isRankMiss;
        return isRankMiss || isRuleMiss;
      });
      return enrichWithHoldings(filtered);
    }

    // Default: 'top20' (Top 20 portfolio selection: ranks 1 to 20)
    const top20List = securities.filter(
      (s) => s.rank !== null && s.rank >= 1 && s.rank <= 20
    );
    return enrichWithHoldings(top20List);
  }, [
    resultsTab,
    changesSubTab,
    nearMissSubTab,
    holdingsSubTab,
    securities,
    holdings,
    buyCandidates,
    enrichWithHoldings,
  ]);

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

  React.useEffect(() => {
    updateScrollWidth();
    const timer = setTimeout(updateScrollWidth, 80);

    const ro = new ResizeObserver(() => {
      updateScrollWidth();
    });

    if (tableScrollRef.current) {
      ro.observe(tableScrollRef.current);
    }
    window.addEventListener('resize', updateScrollWidth);

    return () => {
      clearTimeout(timer);
      ro.disconnect();
      window.removeEventListener('resize', updateScrollWidth);
    };
  }, [updateScrollWidth, filteredSecurities, resultsTab]);

  const handleTopScroll = () => {
    if (isSyncingTop.current) {
      isSyncingTop.current = false;
      return;
    }
    isSyncingBottom.current = true;
    if (tableScrollRef.current && topScrollRef.current) {
      tableScrollRef.current.scrollLeft = topScrollRef.current.scrollLeft;
    }
  };

  const handleTableScroll = () => {
    if (isSyncingBottom.current) {
      isSyncingBottom.current = false;
      return;
    }
    isSyncingTop.current = true;
    if (topScrollRef.current && tableScrollRef.current) {
      topScrollRef.current.scrollLeft = tableScrollRef.current.scrollLeft;
    }
  };

  const scrollToPosition = (x) => {
    if (tableScrollRef.current) {
      tableScrollRef.current.scrollTo({ left: x, behavior: 'smooth' });
    }
  };

  // Empty state rendering
  if (filteredSecurities.length === 0) {
    let emptyTitle = 'No Securities Found';
    let emptyDesc = 'Adjust your sector, region, or search filters to view qualifying companies.';

    if (resultsTab === 'myHoldings') {
      emptyTitle = 'No Holdings in This View';
      emptyDesc = holdings.length === 0
        ? 'No holdings have been imported yet. Click "Upload holdings file" above to import your client portfolio.'
        : 'No holdings match the selected portfolio sub-filter or search criteria.';
    }

    return (
      <div className="bg-white rounded-xl border border-slate-200/90 p-12 text-center shadow-2xs">
        <p className="text-sm font-semibold text-slate-700">{emptyTitle}</p>
        <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">{emptyDesc}</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden">
        {/* Top Synchronized Horizontal Scrollbar */}
        {hasHorizontalOverflow && (
          <div className="bg-slate-50/95 border-b border-slate-200/80">
            {/* Quick Navigation & Helper Header */}
            <div className="px-3.5 py-1.5 flex items-center justify-between gap-2 text-[11px] text-slate-500 bg-slate-50">
              <span className="flex items-center gap-1.5 font-medium text-slate-600">
                <span className="text-[#147b73] font-bold text-xs">↔</span>
                <span>Top Scrollbar · Scroll right to view all sections in this tab</span>
              </span>
              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  type="button"
                  onClick={() => scrollToPosition(0)}
                  className="px-2 py-0.5 rounded bg-white border border-slate-200 hover:bg-slate-100 text-[10px] font-semibold text-slate-600 transition-colors cursor-pointer"
                >
                  ⇤ Rank &amp; Ticker
                </button>
                <button
                  type="button"
                  onClick={() => scrollToPosition(tableScrollWidth * 0.45)}
                  className="px-2 py-0.5 rounded bg-white border border-slate-200 hover:bg-slate-100 text-[10px] font-semibold text-slate-600 transition-colors cursor-pointer"
                >
                  Cause &amp; Attribution
                </button>
                <button
                  type="button"
                  onClick={() => scrollToPosition(tableScrollWidth)}
                  className="px-2 py-0.5 rounded bg-white border border-slate-200 hover:bg-slate-100 text-[10px] font-semibold text-slate-600 transition-colors cursor-pointer"
                >
                  Valuation &amp; Decision ⇥
                </button>
              </div>
            </div>

            {/* Native Top Scrollbar Track */}
            <div
              ref={topScrollRef}
              onScroll={handleTopScroll}
              className="overflow-x-auto overflow-y-hidden custom-top-scrollbar bg-slate-100/70 border-t border-slate-200/60"
              style={{ height: '14px' }}
            >
              <div style={{ width: `${tableScrollWidth}px`, height: '1px' }} />
            </div>
          </div>
        )}

        {/* Main Table Scroll Container (with Bottom Scrollbar) */}
        <div
          ref={tableScrollRef}
          onScroll={handleTableScroll}
          className="overflow-x-auto custom-table-scrollbar"
        >
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-3 text-center whitespace-nowrap min-w-[125px]">
                  Rank ({activeProfileName})
                </th>
                <th className="py-3 px-3 text-center whitespace-nowrap min-w-[115px]">
                  Holding Rank
                </th>
                <th className="py-3 px-3.5 min-w-[200px]">Security &amp; Ticker</th>
                <th className="py-3 px-3.5 whitespace-nowrap">Sector</th>
                <th className="py-3 px-3.5 whitespace-nowrap">Score</th>
                <th className="py-3 px-3.5 whitespace-nowrap">
                  {resultsTab === 'myHoldings' ? 'Model Verdict' : 'Movement'}
                </th>
                <th className="py-3 px-3.5 min-w-[230px]">
                  {resultsTab === 'myHoldings' ? 'Portfolio vs Screening Attribution' : 'Cause / Attribution'}
                </th>
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
                        : item.comparisonStatus === 'held_in_top20'
                        ? 'bg-emerald-50/20'
                        : item.comparisonStatus === 'held_exited' || isExited
                        ? 'bg-rose-50/30'
                        : item.isBuyCandidate
                        ? 'bg-indigo-50/20'
                        : isNew
                        ? 'bg-amber-50/20'
                        : ''
                    }`}
                  >
                    {/* 1. Rank in Active Screening Profile */}
                    <td className="py-3.5 px-3 text-center font-mono text-[11px] whitespace-nowrap">
                      {item.rank !== null && item.rank !== undefined ? (
                        <span className="font-bold text-slate-800 bg-slate-100/90 px-2 py-0.5 rounded text-xs border border-slate-200">
                          #{item.rank}
                        </span>
                      ) : item.prevRank ? (
                        <span className="text-rose-500 line-through text-xs">#{item.prevRank}</span>
                      ) : (
                        <span className="text-slate-400 font-mono text-xs">—</span>
                      )}
                    </td>

                    {/* 2. Rank in Holdings (with rank shift comparison) */}
                    <td className="py-3.5 px-3 text-center font-mono text-[11px] whitespace-nowrap">
                      {item.holdingRank !== null && item.holdingRank !== undefined ? (
                        <div className="inline-flex items-center gap-1 justify-center">
                          <span className="font-bold text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200/80 text-xs">
                            #{item.holdingRank}
                          </span>
                          {item.holdingRankDelta !== null && item.holdingRankDelta !== undefined && (
                            item.holdingRankDelta > 0 ? (
                              <span
                                className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-1 py-0.5 rounded border border-emerald-200/60"
                                title={`Holding #${item.holdingRank} improved to #${item.rank} (+${item.holdingRankDelta})`}
                              >
                                ▲ +{item.holdingRankDelta}
                              </span>
                            ) : item.holdingRankDelta < 0 ? (
                              <span
                                className="text-[10px] font-bold text-rose-600 bg-rose-50 px-1 py-0.5 rounded border border-rose-200/60"
                                title={`Holding #${item.holdingRank} dropped to #${item.rank} (${item.holdingRankDelta})`}
                              >
                                ▼ {item.holdingRankDelta}
                              </span>
                            ) : (
                              <span
                                className="text-[10px] font-semibold text-slate-400"
                                title="Holding rank matches model rank"
                              >
                                =
                              </span>
                            )
                          )}
                        </div>
                      ) : item.isBuyCandidate ? (
                        <span className="text-[10px] font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 px-1.5 py-0.5 rounded whitespace-nowrap">
                          Not Held
                        </span>
                      ) : (
                        <span className="text-slate-400 text-xs">—</span>
                      )}
                    </td>

                    {/* 2. Security Name & Ticker */}
                    <td className="py-3.5 px-3.5">
                      <div className="font-bold text-slate-900 leading-snug">
                        {item.name}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-1.5 font-medium flex-wrap">
                        <span className="font-mono font-semibold text-slate-600">{item.ticker}</span>
                        <span>·</span>
                        <span>{item.country}</span>
                        {item.exchange && (
                          <>
                            <span>·</span>
                            <span className="text-slate-400">{item.exchange}</span>
                          </>
                        )}
                        {item.isHolding && (item.weightPct > 0 || item.shares > 0) && (
                          <>
                            <span>·</span>
                            <span className="font-semibold text-teal-700 bg-teal-50 px-1.5 py-0.2 rounded border border-teal-200/60">
                              {item.weightPct > 0 ? `${item.weightPct}% weight` : `${item.shares.toLocaleString()} shs`}
                            </span>
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
                          {item.score !== undefined && item.score !== null ? item.score : '—'}
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

                    {/* 5. Movement / Model Verdict */}
                    <td className="py-3.5 px-3.5 whitespace-nowrap">
                      {item.isBuyCandidate ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 border border-indigo-200 px-2 py-0.5 text-[10px] font-bold text-indigo-800">
                          ★ BUY IDEA
                        </span>
                      ) : resultsTab === 'myHoldings' && item.isHolding ? (
                        item.comparisonStatus === 'held_in_top20' ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
                            🏆 TOP 20 (#{item.rank})
                          </span>
                        ) : item.comparisonStatus === 'held_exited' ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 border border-rose-200 px-2 py-0.5 text-[10px] font-bold text-rose-700">
                            ▼ EXITED MODEL
                          </span>
                        ) : item.comparisonStatus === 'held_rank_miss' ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-[10px] font-bold text-amber-800">
                            ⚠️ RANK MISS (#{item.rank})
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 border border-slate-200 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
                            ○ UNSCREENED
                          </span>
                        )
                      ) : resultsTab === 'top20' && item.isHeld ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 border border-teal-200 px-2 py-0.5 text-[10px] font-bold text-teal-800">
                          💼 HELD ({item.holdingWeight ? `${item.holdingWeight}%` : 'Held'})
                        </span>
                      ) : resultsTab === 'top20' && item.stageStatus !== 'passed' ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-300 px-2 py-0.5 text-[10px] font-bold text-amber-800">
                          ⚠️ NEAR MISS FILL
                        </span>
                      ) : resultsTab === 'nearMisses' ? (
                        item.nearMissStatus === 'rank_near_miss' || (item.rank !== null && item.rank >= 21 && item.rank <= 40) ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-[10px] font-bold text-amber-800">
                            ⚠️ RANK #{item.rank}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 border border-rose-200 px-2 py-0.5 text-[10px] font-bold text-rose-800">
                            ⚠️ RULE MISS
                          </span>
                        )
                      ) : isNew ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold text-emerald-800">
                          ★ NEW
                        </span>
                      ) : isExited ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 border border-rose-200 px-2 py-0.5 text-[10px] font-bold text-rose-700">
                          ▼ EXITED
                        </span>
                      ) : typeof item.rankDelta === 'string' && item.rankDelta.startsWith('+') ? (
                        <span className="inline-flex items-center gap-0.5 font-bold text-emerald-600 font-mono text-[11px]">
                          ▲ {item.rankDelta}
                        </span>
                      ) : typeof item.rankDelta === 'string' && item.rankDelta.startsWith('-') ? (
                        <span className="inline-flex items-center gap-0.5 font-bold text-rose-600 font-mono text-[11px]">
                          ▼ {item.rankDelta}
                        </span>
                      ) : typeof item.rankDelta === 'number' && item.rankDelta > 0 ? (
                        <span className="inline-flex items-center gap-0.5 font-bold text-emerald-600 font-mono text-[11px]">
                          ▲ +{item.rankDelta}
                        </span>
                      ) : typeof item.rankDelta === 'number' && item.rankDelta < 0 ? (
                        <span className="inline-flex items-center gap-0.5 font-bold text-rose-600 font-mono text-[11px]">
                          ▼ {item.rankDelta}
                        </span>
                      ) : (
                        <span className="text-slate-400 text-[11px] font-mono">—</span>
                      )}
                    </td>

                    {/* 6. Cause / Attribution Badge */}
                    <td className="py-3.5 px-3.5">
                      <div className="text-[11px] font-medium">
                        {item.isBuyCandidate ? (
                          <span className="inline-block rounded-md px-2.5 py-1 text-[11px] font-medium leading-relaxed bg-indigo-50 text-indigo-800 border border-indigo-200/70">
                            Top 20 Model Pick · Fresh idea not currently in client holdings
                          </span>
                        ) : resultsTab === 'myHoldings' && item.isHolding ? (
                          item.comparisonStatus === 'held_in_top20' ? (
                            <span className="inline-block rounded-md px-2.5 py-1 text-[11px] font-medium leading-relaxed bg-emerald-50 text-emerald-800 border border-emerald-200/70">
                              Core Winner: Rank #{item.rank} · Score {item.score}/100 · Allocation: {item.weightPct}%
                            </span>
                          ) : item.comparisonStatus === 'held_exited' ? (
                            <span className="inline-block rounded-md px-2.5 py-1 text-[11px] font-medium leading-relaxed bg-rose-50 text-rose-800 border border-rose-200/70">
                              {item.movementReason || 'Failed knockout gates'} · Allocation: {item.weightPct}%
                            </span>
                          ) : item.comparisonStatus === 'held_rank_miss' ? (
                            <span className="inline-block rounded-md px-2.5 py-1 text-[11px] font-medium leading-relaxed bg-amber-50 text-amber-800 border border-amber-200/70">
                              {item.movementReason || 'Ranked outside Top 20 cutoff'} · Allocation: {item.weightPct}%
                            </span>
                          ) : (
                            <span className="inline-block rounded-md px-2.5 py-1 text-[11px] font-medium leading-relaxed bg-slate-50 text-slate-600 border border-slate-200/60">
                              Not evaluated in current regional run · Allocation: {item.weightPct}%
                            </span>
                          )
                        ) : resultsTab === 'top20' && item.stageStatus !== 'passed' ? (
                          <span className="inline-block rounded-md px-2.5 py-1 text-[11px] font-medium leading-relaxed bg-amber-50 text-amber-800 border border-amber-200/70">
                            {item.movementReason || 'Top 20 Portfolio Selection · Closest near-miss contender'}
                          </span>
                        ) : resultsTab === 'nearMisses' ? (
                          <span className="inline-block rounded-md px-2.5 py-1 text-[11px] font-medium leading-relaxed bg-amber-50 text-amber-800 border border-amber-200/70">
                            {item.movementReason || (item.rank ? `Passed rules · Ranked #${item.rank} (outside Top 20 cutoff)` : 'Close to knockout threshold')}
                          </span>
                        ) : item.movementReason ? (
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

                    {/* 7. Key Valuation */}
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
                          title="Mark position to keep in portfolio"
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
                          title="Mark position to divest / trim"
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
          💡 <strong>Tip:</strong> Click any security row to inspect knockout gates, quality breakdown, and record your Keep / Drop rationale in the drawer.
        </span>
        <span className="font-medium text-slate-600">
          Showing {filteredSecurities.length} {resultsTab === 'myHoldings' ? 'portfolio positions' : 'screened securities'}
        </span>
      </div>
    </div>
  );
};
