import React, { useState, useEffect, useMemo } from 'react';
import {
  AlertCircle,
  ArrowUpRight,
  CheckCircle2,
  ChevronRight,
  HelpCircle,
  Info,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  X,
  PieChart,
  Layers,
  Scale,
  Award
} from 'lucide-react';
import { useScreening } from '../../context/ScreeningContext';

export const SecurityDetailDrawer = () => {
  const {
    selectedSecurity,
    setSelectedSecurityId,
    setSecurityDecision,
    securities = [],
    sectorLimits = {},
    diversification = {},
  } = useScreening();

  const [localReason, setLocalReason] = useState('');
  const [localNote, setLocalNote] = useState('');

  useEffect(() => {
    if (selectedSecurity) {
      setLocalReason(selectedSecurity.decisionReason || '');
      setLocalNote(selectedSecurity.decisionNote || '');
    }
  }, [selectedSecurity]);

  // Normalize metric items from scoreBreakdown
  const normalizedMetrics = useMemo(() => {
    if (!selectedSecurity?.scoreBreakdown) return [];
    return selectedSecurity.scoreBreakdown.map((m) => {
      const maxScore = m.max_score ?? m.maxScore ?? 0;
      const score = m.score ?? 0;
      const percentage = m.percentage ?? (maxScore > 0 ? (score / maxScore) * 100 : 0);
      const name = m.name || '';
      const nameLower = name.toLowerCase();

      // Determine if rule is a knockout gate
      const isKnownFloor =
        nameLower.includes('debt') ||
        nameLower.includes('volume') ||
        nameLower.includes('traded value') ||
        nameLower.includes('market cap') ||
        nameLower.includes('confidence');

      const mode = m.mode || (maxScore === 0 || isKnownFloor ? 'Req.' : 'Score');
      const isGate = mode === 'Req.' || mode === 'Both' || maxScore === 0 || isKnownFloor;
      const isScoring = mode === 'Score' || mode === 'Both' || maxScore > 0;

      // Determine category if not explicitly provided
      let category = m.category || 'Quality';
      if (nameLower.includes('p/e') || nameLower.includes('sales') || nameLower.includes('cash flow') || nameLower.includes('ev /') || nameLower.includes('peg')) {
        category = 'Valuation';
      } else if (nameLower.includes('growth')) {
        category = 'Growth';
      } else if (nameLower.includes('beta') || nameLower.includes('debt')) {
        category = 'Financial Health';
      } else if (nameLower.includes('volume') || nameLower.includes('cap') || nameLower.includes('traded')) {
        category = 'Size & Liquidity';
      }

      return {
        name,
        category,
        mode,
        isGate,
        isScoring,
        score,
        maxScore,
        valueDisplay: m.value_display ?? m.valueDisplay ?? 'n/a',
        benchmarkDisplay: m.benchmark_display ?? m.benchmarkDisplay ?? '',
        percentage: Math.min(100, Math.max(0, percentage)),
        status: m.status || 'full',
        passed: m.passed !== undefined ? m.passed : m.status !== 'miss',
        failureReason: m.failure_reason || m.failureReason || null,
      };
    });
  }, [selectedSecurity]);

  // Separate Knockout Gates from Quality Scoring Rules
  const knockoutGates = useMemo(() => {
    return normalizedMetrics.filter((m) => m.isGate);
  }, [normalizedMetrics]);

  const scoringMetrics = useMemo(() => {
    return normalizedMetrics.filter((m) => m.isScoring);
  }, [normalizedMetrics]);

  // Compute portfolio quota context
  const portfolioStats = useMemo(() => {
    if (!selectedSecurity || !securities.length) {
      return { sectorCount: 1, countryCount: 1, top20Count: 20 };
    }
    const top20 = securities.filter(
      (s) => (s.rank && s.rank <= 20) || (s.stageStatus === 'passed' && s.rank <= 20)
    );
    const sectorCount = top20.filter((s) => s.sector === selectedSecurity.sector).length;
    const countryCount = top20.filter((s) => s.country === selectedSecurity.country).length;
    return {
      sectorCount,
      countryCount,
      top20Count: top20.length || 20,
    };
  }, [selectedSecurity, securities]);

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

  const isExited =
    selectedSecurity.deltaStatus === 'exited' ||
    selectedSecurity.rankDelta === 'EXITED' ||
    selectedSecurity.stageStatus === 'exited';

  const isNew =
    selectedSecurity.deltaStatus === 'entered' ||
    selectedSecurity.rankDelta === 'NEW';

  const isRankNearMiss =
    selectedSecurity.nearMissStatus === 'rank_near_miss' ||
    (selectedSecurity.rank && selectedSecurity.rank >= 21 && selectedSecurity.rank <= 40);

  const isRuleNearMiss =
    selectedSecurity.nearMissStatus === 'rule_near_miss' ||
    selectedSecurity.deltaStatus === 'rule_miss';

  const hasBankExemption = normalizedMetrics.some((m) => m.status === 'exempt');
  const failedGates = knockoutGates.filter((g) => !g.passed && g.status !== 'exempt');
  const passedGatesCount = knockoutGates.length - failedGates.length;

  // Find top score contributor and lowest metric
  const sortedScoring = [...scoringMetrics].sort((a, b) => b.score - a.score);
  const topContributor = sortedScoring.length > 0 ? sortedScoring[0] : null;

  return (
    <div className="w-[490px] bg-white border-l border-slate-200/90 shadow-2xl flex flex-col h-full shrink-0 z-20 overflow-y-auto">
      {/* ── HEADER ── */}
      <div className="p-6 border-b border-slate-100 flex items-start justify-between bg-slate-50/70 sticky top-0 z-10 backdrop-blur-sm">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
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
            {!isExited && selectedSecurity.rank && selectedSecurity.rank <= 20 && (
              <span className="rounded bg-teal-100 border border-teal-300 px-1.5 py-0.5 text-[10px] font-bold text-[#147b73]">
                TOP 20 · RANK #{selectedSecurity.rank}
              </span>
            )}
            {isRankNearMiss && !isExited && (
              <span className="rounded bg-amber-50 border border-amber-200 px-1.5 py-0.5 text-[10px] font-bold text-amber-800">
                NEAR MISS · RANK #{selectedSecurity.rank}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1.5 font-medium flex items-center gap-1.5 flex-wrap">
            <span className="font-mono font-bold text-slate-700">{selectedSecurity.ticker}</span>
            <span>·</span>
            <span>{selectedSecurity.exchange || 'Exchange'}</span>
            <span>·</span>
            <span>{selectedSecurity.sector}</span>
            <span>·</span>
            <span>{selectedSecurity.country}</span>
            <span>·</span>
            <span className="px-1.5 py-0.5 bg-slate-200/70 text-slate-700 rounded text-[10px] font-semibold">
              {selectedSecurity.marketCapCategory || 'Large Cap'}
            </span>
          </p>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          <div className="text-right">
            <span className="block text-[9px] font-bold tracking-wider text-slate-400 uppercase">
              Total Score
            </span>
            <div className="flex items-baseline justify-end gap-1">
              <span className="text-2xl font-bold font-serif text-slate-900 leading-none">
                {selectedSecurity.score}
              </span>
              <span className="text-[11px] font-semibold text-slate-400">/100</span>
              {selectedSecurity.prevScore !== undefined &&
                selectedSecurity.prevScore !== null &&
                selectedSecurity.score !== selectedSecurity.prevScore && (
                  <span
                    className={`text-xs font-bold ${
                      selectedSecurity.score > selectedSecurity.prevScore
                        ? 'text-emerald-600'
                        : 'text-rose-600'
                    }`}
                  >
                    {selectedSecurity.score > selectedSecurity.prevScore
                      ? `+${selectedSecurity.score - selectedSecurity.prevScore}`
                      : selectedSecurity.score - selectedSecurity.prevScore}
                  </span>
                )}
            </div>
          </div>
          <button
            onClick={() => setSelectedSecurityId(null)}
            className="text-slate-400 hover:text-slate-700 p-1.5 text-base transition-colors rounded-lg hover:bg-slate-200/60 cursor-pointer"
            title="Close Drawer"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      <div className="p-6 space-y-6 text-slate-700">
        {/* ── 1. EXECUTIVE QUALIFICATION SUMMARY CARD ── */}
        <div
          className={`rounded-xl border p-4 text-xs space-y-2.5 shadow-xs ${
            isExited
              ? 'border-rose-200 bg-rose-50/60 text-rose-950'
              : isRuleNearMiss
              ? 'border-amber-200 bg-amber-50/50 text-amber-950'
              : isRankNearMiss
              ? 'border-amber-200 bg-amber-50/40 text-amber-950'
              : 'border-teal-200 bg-teal-50/40 text-teal-950'
          }`}
        >
          <div className="flex items-center justify-between border-b border-black/10 pb-2">
            <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[11px]">
              {isExited ? (
                <>
                  <ShieldAlert size={15} className="text-rose-600" />
                  <span className="text-rose-800">Disqualification Verdict</span>
                </>
              ) : isRankNearMiss || isRuleNearMiss ? (
                <>
                  <AlertCircle size={15} className="text-amber-600" />
                  <span className="text-amber-800">Near-Miss Classification</span>
                </>
              ) : (
                <>
                  <ShieldCheck size={15} className="text-[#147b73]" />
                  <span className="text-[#147b73]">Executive Qualification Verdict</span>
                </>
              )}
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-white/70 border border-black/10">
              {isExited
                ? 'EXITED RUN'
                : selectedSecurity.rank
                ? `RANK #${selectedSecurity.rank} OF ${securities.length || 186}`
                : 'QUALIFIED'}
            </span>
          </div>

          {/* Dynamic Explanation Sentence */}
          <p className="text-[12px] leading-relaxed font-medium">
            {isExited ? (
              <>
                <strong>Disqualified from Top 20: </strong>
                {failedGates.length > 0
                  ? `${failedGates[0].name} (${failedGates[0].valueDisplay}) breached the screening limit of ${failedGates[0].benchmarkDisplay}.`
                  : 'Fell below the fundamental quality floor or was displaced during sector rebalancing.'}
              </>
            ) : isRuleNearMiss ? (
              <>
                <strong>Narrow Rule Near-Miss: </strong>
                Passed general screening floors but failed a single gate by under 5% (
                {failedGates[0] ? `${failedGates[0].name}: ${failedGates[0].valueDisplay}` : 'Gate threshold'}
                ).
              </>
            ) : isRankNearMiss ? (
              <>
                <strong>Passed All Knockout Gates: </strong>
                {selectedSecurity.decisionReason && selectedSecurity.decisionReason.toLowerCase().includes('limit') ? (
                  <>
                    Achieved a strong quality score of <strong>{selectedSecurity.score}/100</strong>, but <strong>{selectedSecurity.decisionReason.toLowerCase()}</strong> in the Top 20 portfolio.
                  </>
                ) : (
                  <>
                    Achieved a strong quality score of <strong>{selectedSecurity.score}/100</strong>, but ranked at #{selectedSecurity.rank}, falling just outside the Top 20 threshold.
                  </>
                )}
              </>
            ) : (
              <>
                <strong>Fully Qualified: </strong>
                Passed 100% of mandatory knockout gates. Awarded <strong>Rank #{selectedSecurity.rank}</strong> with an aggregate score of <strong>{selectedSecurity.score}/100</strong>
                {topContributor ? `, driven by superior ${topContributor.name} (${topContributor.valueDisplay})` : ''}.
              </>
            )}
          </p>

          {/* Rule comparison if previous delta exists */}
          {selectedSecurity.ruleComparison && (
            <div className="pt-2 border-t border-black/10 text-[11px] space-y-1">
              <div className="flex justify-between font-medium">
                <span className="text-slate-600">Rule Trigger:</span>
                <span className="font-bold">{selectedSecurity.ruleComparison.metric}</span>
              </div>
              <div className="flex justify-between font-medium">
                <span className="text-slate-600">Stock Actual:</span>
                <span className="font-mono font-bold">{selectedSecurity.ruleComparison.stockValue}</span>
              </div>
            </div>
          )}
        </div>

        {/* ── 2. MANDATORY KNOCKOUT GATES (PASS/FAIL AUDIT) ── */}
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <div>
              <h3 className="text-[11px] font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck size={14} className="text-[#147b73]" />
                <span>1. Mandatory Knockout Gates</span>
              </h3>
              <p className="text-[11px] text-slate-500">
                Must pass 100% of these floors to qualify for ranking
              </p>
            </div>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                failedGates.length === 0
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-rose-50 text-rose-700 border-rose-200'
              }`}
            >
              {passedGatesCount} / {knockoutGates.length} Passed
            </span>
          </div>

          <div className="rounded-lg border border-slate-200 overflow-hidden shadow-2xs divide-y divide-slate-100 bg-white">
            {knockoutGates.length > 0 ? (
              knockoutGates.map((gate, idx) => {
                const isExempt = gate.status === 'exempt';
                const isPassed = gate.passed || isExempt;

                return (
                  <div key={idx} className="p-3 flex items-center justify-between text-xs hover:bg-slate-50/60 transition-colors">
                    <div className="space-y-0.5">
                      <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                        <span>{gate.name}</span>
                        {isExempt && (
                          <span className="px-1.5 py-0.2 bg-teal-50 text-[#147b73] border border-teal-200 rounded text-[9px] font-bold">
                            Bank Exempt
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        Actual: <strong className="text-slate-800">{gate.valueDisplay}</strong>
                        {gate.benchmarkDisplay && (
                          <span className="text-slate-400"> (Limit: {gate.benchmarkDisplay})</span>
                        )}
                      </div>
                      {gate.failureReason && (
                        <div className="text-[10px] text-rose-600 font-medium pt-0.5">
                          {gate.failureReason}
                        </div>
                      )}
                    </div>

                    <div className="shrink-0 text-right">
                      {isExempt ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-bold bg-teal-50 text-[#147b73] border border-teal-200">
                          <CheckCircle2 size={12} /> EXEMPT
                        </span>
                      ) : isPassed ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 size={12} /> PASS
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                          <ShieldAlert size={12} /> BREACH
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-3 text-xs text-slate-400">No active knockout gates defined in current profile.</div>
            )}
          </div>
        </div>

        {/* ── 3. QUALITY & VALUATION SCORING (RANK ATTRIBUTION) ── */}
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <div>
              <h3 className="text-[11px] font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <Award size={14} className="text-[#147b73]" />
                <span>2. Quality Scoring &amp; Rank Attribution</span>
              </h3>
              <p className="text-[11px] text-slate-500">
                Points awarded determining Rank #{selectedSecurity.rank || 'N/A'} (0 to 100 Scale)
              </p>
            </div>
            <span className="text-[11px] font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
              {selectedSecurity.score} / 100 pts
            </span>
          </div>

          <div className="space-y-2.5">
            {scoringMetrics.length > 0 ? (
              scoringMetrics.map((metric, idx) => {
                const isExempt = metric.status === 'exempt';
                const isMiss = metric.status === 'miss';
                const isThreshold = metric.status === 'threshold';
                const isFull = metric.status === 'full';

                return (
                  <div
                    key={idx}
                    className="rounded-lg border border-slate-200/90 bg-[#fdfefe] p-3 text-xs shadow-2xs space-y-2 hover:border-slate-300 transition-colors"
                  >
                    <div className="flex justify-between items-baseline">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-slate-800">{metric.name}</span>
                        <span className="px-1.5 py-0.2 bg-slate-100 text-slate-600 rounded text-[9px] font-medium border border-slate-200/60">
                          {metric.category}
                        </span>
                      </div>
                      <div className="font-mono text-[11px] font-bold text-slate-800">
                        {isExempt ? (
                          <span className="text-[#147b73]">Bank Exempt</span>
                        ) : (
                          `${metric.score} / ${metric.maxScore} pts`
                        )}
                      </div>
                    </div>

                    {/* Visual Score Meter */}
                    {!isExempt && metric.maxScore > 0 && (
                      <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden border border-slate-200/60">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${
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

                    <div className="flex justify-between items-center text-[11px] text-slate-500 pt-0.5">
                      <span>
                        Actual: <strong className="text-slate-800 font-mono">{metric.valueDisplay}</strong>
                      </span>
                      {metric.benchmarkDisplay && (
                        <span>
                          Target: <strong className="text-slate-700 font-mono">{metric.benchmarkDisplay}</strong>
                        </span>
                      )}
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                          isFull
                            ? 'text-emerald-700 bg-emerald-50'
                            : isThreshold
                            ? 'text-amber-700 bg-amber-50'
                            : isExempt
                            ? 'text-[#147b73] bg-teal-50'
                            : 'text-rose-700 bg-rose-50'
                        }`}
                      >
                        {isFull ? '100% Pts' : isThreshold ? 'Partial' : isExempt ? 'Exempt' : '0 Pts'}
                      </span>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-slate-400">Detailed metric breakdown unavailable.</p>
            )}
          </div>
        </div>

        {/* ── 4. PORTFOLIO & SECTOR GUARDRAILS ── */}
        <div>
          <h3 className="text-[11px] font-bold text-slate-900 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
            <PieChart size={14} className="text-[#147b73]" />
            <span>3. Portfolio &amp; Sector Guardrails</span>
          </h3>
          <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3.5 space-y-2.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-600 font-medium">Sector Representation:</span>
              <span className="font-bold text-slate-800">
                {selectedSecurity.sector} ({portfolioStats.sectorCount} stocks in Top 20)
              </span>
            </div>
            {selectedSecurity.decisionReason && selectedSecurity.decisionReason.toLowerCase().includes('sector limit') && (
              <div className="rounded-md border border-amber-200 bg-amber-50/80 p-2 text-[11px] font-semibold text-amber-900">
                ⚠️ {selectedSecurity.decisionReason}: {portfolioStats.sectorCount} higher-scoring {selectedSecurity.sector} names were selected ahead into the Top 20.
              </div>
            )}
            <div className="flex items-center justify-between border-t border-slate-200/60 pt-2">
              <span className="text-slate-600 font-medium">Country Quota:</span>
              <span className="font-bold text-slate-800">
                {selectedSecurity.country} ({portfolioStats.countryCount} stocks in Top 20)
              </span>
            </div>
            <div className="flex items-center justify-between border-t border-slate-200/60 pt-2">
              <span className="text-slate-600 font-medium">Institution Exemption:</span>
              <span className="font-semibold text-slate-700">
                {hasBankExemption
                  ? 'Bank Exemption Applied (Leverage gates waived)'
                  : 'Standard Corporate Balance Sheet Rules'}
              </span>
            </div>
          </div>
        </div>

        {/* ── 5. RANK PROGRESSION HISTORY ── */}
        <div>
          <h3 className="text-[11px] font-bold text-slate-900 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
            <TrendingUp size={14} className="text-[#147b73]" />
            <span>4. Rank History (Last Executed Runs)</span>
          </h3>
          <div className="rounded-lg border border-slate-200 bg-[#fdfefe] p-3 text-xs font-mono text-slate-700 flex items-center space-x-2 flex-wrap">
            {selectedSecurity.rankHistory && selectedSecurity.rankHistory.length > 0 ? (
              selectedSecurity.rankHistory.map((rnk, i) => {
                const isLast = i === selectedSecurity.rankHistory.length - 1;
                return (
                  <React.Fragment key={i}>
                    <span
                      className={`px-2.5 py-1 rounded font-bold text-xs ${
                        isLast
                          ? rnk === 'EXIT'
                            ? 'bg-rose-100 text-rose-800 border border-rose-200'
                            : 'bg-teal-100 text-[#147b73] border border-teal-200'
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
              <span className="font-bold text-teal-800 bg-teal-50 px-2.5 py-1 rounded border border-teal-200">
                #{selectedSecurity.rank || '1'}
              </span>
            )}
          </div>
        </div>

        {/* ── 6. DATA SOURCES & CONFIDENCE ── */}
        <div>
          <h3 className="text-[11px] font-bold text-slate-900 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Info size={14} className="text-[#147b73]" />
            <span>5. Data Lineage &amp; Reliability</span>
          </h3>
          <div className="bg-[#fcfdfd] border border-slate-200/80 rounded-lg p-3 space-y-1.5 text-xs">
            <div className="flex items-start justify-between gap-2">
              <span className="text-slate-700 font-medium">
                {selectedSecurity.confidenceDetails?.estimateNote ||
                  'Consensus estimates verified across financial vendor feeds'}
              </span>
              <span className="shrink-0 px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold rounded">
                High Confidence
              </span>
            </div>
            <div className="text-[11px] text-slate-400">
              {selectedSecurity.confidenceDetails?.freshnessNote ||
                'Fundamentals refreshed for current active quarter'}
            </div>
          </div>
        </div>

        {/* ── 7. ANALYST ACTION (KEEP / DROP DECISION) ── */}
        <div className="pt-2 border-t border-slate-200">
          <h3 className="text-[11px] font-bold text-slate-900 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
            <Scale size={14} className="text-[#147b73]" />
            <span>6. Your Investment Decision</span>
          </h3>
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => handleDecision('keep')}
                className={`flex-1 py-2 text-xs font-semibold rounded-md transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                  selectedSecurity.decision === 'keep'
                    ? 'bg-[#147b73] text-white shadow-xs'
                    : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
                }`}
              >
                <CheckCircle2 size={14} />
                <span>Keep in Portfolio</span>
              </button>
              <button
                type="button"
                onClick={() => handleDecision('drop')}
                className={`flex-1 py-2 text-xs font-semibold rounded-md transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                  selectedSecurity.decision === 'drop'
                    ? 'bg-rose-600 text-white shadow-xs'
                    : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
                }`}
              >
                <ShieldAlert size={14} />
                <span>Drop / Divest</span>
              </button>
            </div>

            {/* Decision Reason Dropdown */}
            <div>
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

            {/* Analyst Note Input */}
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
