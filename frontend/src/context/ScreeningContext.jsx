import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  INITIAL_COUNTRIES,
  INITIAL_DIVERSIFICATION,
  INITIAL_EXCHANGES,
  INITIAL_FUNNEL,
  INITIAL_RUN_HISTORY,
  INITIAL_RULE_METRICS,
  INITIAL_SECTORS,
  INITIAL_SCHEDULE,
  INITIAL_SECTOR_LIMITS,
  INITIAL_SECURITIES,
  MOCK_SECURITIES_BY_RUN,
} from '../data/mockData';
import {
  fetchProfiles as fetchProfilesApi,
  createProfile as createProfileApi,
  updateProfile as updateProfileApi,
  activateProfile as activateProfileApi,
  deleteProfile as deleteProfileApi,
  fetchScreeningResults,
  fetchRunComparison,
  initiateScreening,
  fetchScreeningRuns,
  recordDecisionApi,
  fetchDecisionsApi,
} from '../services/api';

const ScreeningContext = createContext(null);

function reconstructSnapshotFromBackend(bp) {
  const rulesMap = new Map();
  (bp.rules || []).forEach((r) => {
    if (r.name) rulesMap.set(r.name.toLowerCase(), r);
    if (r.metric_name) rulesMap.set(r.metric_name.toLowerCase(), r);
    if (r.id) rulesMap.set(r.id.toLowerCase(), r);
    const normalizedKey = (r.name || r.metric_name || r.id || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
    if (normalizedKey) rulesMap.set(normalizedKey, r);
  });

  const metrics = INITIAL_RULE_METRICS.map((metric) => {
    const rawKey = metric.name.toLowerCase();
    const normalizedKey = rawKey.replace(/[^a-z0-9]+/g, '');
    const matched = rulesMap.get(rawKey) || rulesMap.get(normalizedKey);
    if (matched) {
      return {
        ...metric,
        mode: matched.mode || 'Both',
        condition: matched.condition || '>=',
        value: matched.value !== undefined ? String(matched.value) : String(matched.threshold_value ?? ''),
        weight: matched.weight !== undefined ? matched.weight : 0,
      };
    }
    return { ...metric, mode: 'Off', condition: '', value: '', weight: 0 };
  });

  const sectorLimitsMap = bp.sector_limits || {};
  const sectorLimits = INITIAL_SECTOR_LIMITS.map((sl) => {
    if (sectorLimitsMap[sl.sector] !== undefined) {
      return { ...sl, limit: String(sectorLimitsMap[sl.sector]) };
    }
    return { ...sl };
  });

  const selectedCountryList = Array.isArray(bp.selected_countries) ? bp.selected_countries : [];
  const selectedCountrySet = new Set(selectedCountryList.map((c) => String(c).toLowerCase().trim()));
  const countries = INITIAL_COUNTRIES.map((c) => ({
    ...c,
    selected: selectedCountrySet.size > 0
      ? selectedCountrySet.has(c.name.toLowerCase().trim()) || selectedCountrySet.has(c.id.toLowerCase().trim())
      : c.selected,
  }));

  const savedSnapshot = bp.diversification_rules?.snapshot;
  const savedExchanges = savedSnapshot?.exchanges || [];
  const selectedExchSet = new Set(savedExchanges.filter((e) => e.selected).map((e) => e.id.toLowerCase()));

  const exchanges = INITIAL_EXCHANGES.map((e) => ({
    ...e,
    selected: selectedExchSet.size > 0 ? selectedExchSet.has(e.id.toLowerCase()) : e.selected,
  }));

  return {
    metrics,
    sectorLimits,
    countries,
    exchanges,
    sectors: INITIAL_SECTORS.map((s) => ({ ...s })),
    diversification: { ...INITIAL_DIVERSIFICATION },
  };
}

export function computeProfileVersionDiff(newSnapshot, prevSnapshot) {
  if (!prevSnapshot) {
    const activeRules = (newSnapshot?.metrics || []).filter((m) => m.mode !== 'Off' && m.value !== '');
    const selectedCountries = (newSnapshot?.countries || []).filter((c) => c.selected);
    const countryInfo = selectedCountries.length > 0 ? `, ${selectedCountries.length} countries` : '';
    return [
      `Initial profile created with ${activeRules.length} active rules${countryInfo}`,
    ];
  }

  const diffs = [];
  const prevMetricsMap = new Map();
  (prevSnapshot.metrics || []).forEach((m) => {
    prevMetricsMap.set(m.name.toLowerCase(), m);
  });

  // 1. Compare screening metrics
  (newSnapshot.metrics || []).forEach((curr) => {
    const prev = prevMetricsMap.get(curr.name.toLowerCase());
    if (!prev) {
      if (curr.mode !== 'Off') {
        diffs.push(`Added rule ${curr.name}: ${curr.mode}, ${curr.condition} ${curr.value}`);
      }
      return;
    }

    const prevMode = prev.mode || 'Off';
    const currMode = curr.mode || 'Off';
    const prevCond = prev.condition || '';
    const currCond = curr.condition || '';
    const prevVal = String(prev.value ?? '').trim();
    const currVal = String(curr.value ?? '').trim();
    const prevWeight = Number(prev.weight) || 0;
    const currWeight = Number(curr.weight) || 0;

    // Disabled from active
    if (prevMode !== 'Off' && currMode === 'Off') {
      diffs.push(`${curr.name}: Disabled (was ${prevMode}, ${prevCond} ${prevVal})`);
      return;
    }

    // Enabled from Off
    if (prevMode === 'Off' && currMode !== 'Off') {
      diffs.push(`${curr.name}: Enabled (${currMode}, ${currCond} ${currVal}${currWeight > 0 ? `, weight: ${currWeight}%` : ''})`);
      return;
    }

    // Both active: compare details
    if (currMode !== 'Off') {
      const parts = [];
      if (prevMode !== currMode) {
        parts.push(`Mode: ${currMode} (was ${prevMode})`);
      }
      if (prevCond !== currCond || prevVal !== currVal) {
        parts.push(`Threshold: ${currCond} ${currVal} (was ${prevCond} ${prevVal})`);
      }
      if (prevWeight !== currWeight && (currMode === 'Score' || currMode === 'Both')) {
        parts.push(`Weight: ${currWeight}% (was ${prevWeight}%)`);
      }
      if (parts.length > 0) {
        diffs.push(`${curr.name}: ${parts.join(', ')}`);
      }
    }
  });

  // Check metrics removed from list
  const currMetricsMap = new Map((newSnapshot.metrics || []).map((m) => [m.name.toLowerCase(), m]));
  (prevSnapshot.metrics || []).forEach((prev) => {
    if (!currMetricsMap.has(prev.name.toLowerCase()) && prev.mode !== 'Off') {
      diffs.push(`Removed rule: ${prev.name}`);
    }
  });

  // 2. Compare Sector Debt Limits
  const prevSectorLimitsMap = new Map((prevSnapshot.sectorLimits || []).map((s) => [s.sector, s]));
  (newSnapshot.sectorLimits || []).forEach((currSl) => {
    const prevSl = prevSectorLimitsMap.get(currSl.sector);
    const currLimit = String(currSl.limit ?? '').trim();
    const prevLimit = String(prevSl?.limit ?? '').trim();
    if (currLimit !== prevLimit) {
      if (currLimit && !prevLimit) {
        diffs.push(`${currSl.sector} Debt Limit: Set to ${currLimit}x`);
      } else if (!currLimit && prevLimit) {
        diffs.push(`${currSl.sector} Debt Limit: Removed (was ${prevLimit}x)`);
      } else if (currLimit && prevLimit) {
        diffs.push(`${currSl.sector} Debt Limit: Changed to ${currLimit}x (was ${prevLimit}x)`);
      }
    }
  });

  // 3. Compare Diversification Constraints
  const prevDiv = prevSnapshot.diversification || {};
  const currDiv = newSnapshot.diversification || {};
  const divFields = [
    { key: 'maxNamesPerSector', label: 'Max stocks per sector' },
    { key: 'maxNamesPerCountry', label: 'Max stocks per country' },
    { key: 'minNonUsNamesPct', label: 'Min Non-US weight %' },
    { key: 'minSmallMidCapNames', label: 'Min Small/Mid cap stocks' },
  ];
  divFields.forEach(({ key, label }) => {
    const currVal = String(currDiv[key] ?? '').trim();
    const prevVal = String(prevDiv[key] ?? '').trim();
    if (currVal !== prevVal) {
      if (currVal && !prevVal) {
        diffs.push(`${label}: Set to ${currVal}`);
      } else if (!currVal && prevVal) {
        diffs.push(`${label}: Removed (was ${prevVal})`);
      } else if (currVal && prevVal) {
        diffs.push(`${label}: Changed to ${currVal} (was ${prevVal})`);
      }
    }
  });

  // 4. Compare Universe Countries
  const prevCountries = new Set(
    (prevSnapshot.countries || []).filter((c) => c.selected).map((c) => c.name)
  );
  const currCountries = new Set(
    (newSnapshot.countries || []).filter((c) => c.selected).map((c) => c.name)
  );

  const addedCountries = [...currCountries].filter((c) => !prevCountries.has(c));
  const removedCountries = [...prevCountries].filter((c) => !currCountries.has(c));

  addedCountries.forEach((c) => diffs.push(`Added country: ${c}`));
  removedCountries.forEach((c) => diffs.push(`Removed country: ${c}`));

  // 5. Compare Universe Exchanges
  const prevExchanges = new Set(
    (prevSnapshot.exchanges || []).filter((e) => e.selected).map((e) => e.name)
  );
  const currExchanges = new Set(
    (newSnapshot.exchanges || []).filter((e) => e.selected).map((e) => e.name)
  );

  const addedExchanges = [...currExchanges].filter((e) => !prevExchanges.has(e));
  const removedExchanges = [...prevExchanges].filter((e) => !currExchanges.has(e));

  addedExchanges.forEach((e) => diffs.push(`Added exchange: ${e}`));
  removedExchanges.forEach((e) => diffs.push(`Removed exchange: ${e}`));

  return diffs.length > 0 ? diffs : ['No criteria modifications detected compared to previous version'];
}

function mapBackendProfilesToFrontend(backendProfiles) {
  const parsedProfiles = [];
  const parsedHistory = [];

  backendProfiles.forEach((bp) => {
    const profileKey = bp.profile_name.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    const versionNumber = parseInt(String(bp.version_number).replace(/\D/g, '')) || 1;
    const versionStr = `v${versionNumber}`;
    const snapshot = bp.diversification_rules?.snapshot || reconstructSnapshotFromBackend(bp);
    const changes = bp.changes || bp.diversification_rules?.changes || [];
    const selectedCountries = bp.selected_countries?.length > 0
      ? bp.selected_countries
      : (snapshot.countries || []).filter((c) => c.selected).map((c) => c.name);
    const changeSummary = changes.length > 0
      ? (versionNumber === 1
          ? changes[0]
          : `${changes.length} change${changes.length === 1 ? '' : 's'} compared to v${versionNumber - 1}`)
      : `Saved screening rules (${versionStr})`;

    const profileItem = {
      id: bp.version_id,
      profileKey,
      name: bp.profile_name,
      badge: bp.is_active ? 'Active' : 'Saved',
      description: bp.description || `Saved screening rules (${versionStr})`,
      version: versionStr,
      versionNumber,
      changes,
      selectedCountries,
      snapshot,
    };
    parsedProfiles.push(profileItem);

    const historyItem = {
      id: bp.version_id,
      profileKey,
      versionNumber,
      version: versionStr,
      isCurrent: bp.is_active,
      date: bp.updated_at
        ? new Date(bp.updated_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
        : 'Saved',
      by: 'PM',
      name: bp.profile_name,
      changeSummary,
      resultImpact: '-',
      changes,
      selectedCountries,
      snapshot,
    };
    parsedHistory.push(historyItem);
  });

  return { parsedProfiles, parsedHistory };
}

const createDefaultRuleMetrics = () =>
  INITIAL_RULE_METRICS.map((metric) => ({
    ...metric,
    mode: 'Off',
    condition: '',
    value: '',
    weight: 0,
  }));

const CANONICAL_METRIC_IDS = {
  'Price (USD-equiv.)': 'price_usd',
  'Market cap (USD)': 'market_cap',
  'Avg daily volume (shares)': 'avg_volume',
  'Avg daily traded value (USD)': 'avg_traded_value',
  'Price / sales': 'price_to_sales',
  'Forward P/E vs S&P 500': 'pe_vs_benchmark',
  'Forward P/E': 'forward_pe',
  'PEG': 'peg',
  'EV / EBITDA': 'ev_ebitda',
  'Price / cash flow': 'price_to_cash_flow',
  'Revenue growth (5y, fwd)': 'revenue_growth_fwd',
  'EPS growth (5y, fwd)': 'eps_growth_fwd',
  'Beta': 'beta',
  'Net debt / EBITDA': 'net_debt_ebitda',
  'Dividend yield': 'dividend_yield',
  'Data confidence': 'data_confidence',
  '3y / 5y return': 'return_3y_5y',
};

const parseProfileRuleValue = (val) => {
  if (val === '' || val === undefined || val === null) return null;
  const str = String(val).replace(/[$,x%]/g, '').trim().toLowerCase();
  if (str === 'high') return 3.0;
  if (str === 'medium' || str === 'med') return 2.0;
  if (str === 'low') return 1.0;
  if (str.endsWith('b')) {
    const n = parseFloat(str.slice(0, -1));
    return isNaN(n) ? null : n * 1_000_000_000;
  }
  if (str.endsWith('m')) {
    const n = parseFloat(str.slice(0, -1));
    return isNaN(n) ? null : n * 1_000_000;
  }
  if (str.endsWith('k')) {
    const n = parseFloat(str.slice(0, -1));
    return isNaN(n) ? null : n * 1_000;
  }
  const n = parseFloat(str);
  return isNaN(n) ? null : n;
};

export const ScreeningProvider = ({ children }) => {
  const [activeNav, setActiveNav] = useState('rules'); // 'rules' | 'results' | 'schedule'
  const [rulesTab, setRulesTab] = useState('profiles'); // 'configuration' | 'profiles'
  const [resultsTab, setResultsTab] = useState('top20'); // 'top20' | 'changes' | 'nearMisses' | 'myHoldings'
  const [changesSubTab, setChangesSubTab] = useState('all'); // 'all' | 'entered' | 'exited'
  const [nearMissSubTab, setNearMissSubTab] = useState('all'); // 'all' | 'rank' | 'rule'
  const [selectedProfileName, setSelectedProfileName] = useState('No active profile');
  const [draftProfileName, setDraftProfileName] = useState('');

  const [securities, setSecurities] = useState([]);
  const [selectedSecurityId, setSelectedSecurityId] = useState(null);

  const [filterSector, setFilterSector] = useState('All');
  const [filterRegion, setFilterRegion] = useState('All');
  const [filterCap, setFilterCap] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  const [funnelState, setFunnelState] = useState(INITIAL_FUNNEL);
  const [scheduleConfig, setScheduleConfig] = useState(INITIAL_SCHEDULE);
  const [runHistory, setRunHistory] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [compareRunId, setCompareRunId] = useState('none');
  const [backendRunComparison, setBackendRunComparison] = useState(null);
  const [isScreeningRunning, setIsScreeningRunning] = useState(false);
  const [screeningError, setScreeningError] = useState(null);
  const [screeningRunSuccess, setScreeningRunSuccess] = useState(null);

  // Dual-mode run results loader: PostgreSQL Backend first, Mock fallback
  useEffect(() => {
    let isMounted = true;

    async function loadResults() {
      if (!selectedRunId) {
        if (isMounted) setSecurities([]);
        return;
      }

      try {
        const [realResults, runDecisions, profileDecisions] = await Promise.all([
          fetchScreeningResults(selectedRunId),
          fetchDecisionsApi(selectedRunId).catch(() => []),
          fetchDecisionsApi(null, currentRun?.rules).catch(() => []),
        ]);
        const decisionMap = new Map();
        (profileDecisions || []).forEach((d) => {
          if (d.canonical_company_id) decisionMap.set(d.canonical_company_id, d);
        });
        (runDecisions || []).forEach((d) => {
          if (d.canonical_company_id) decisionMap.set(d.canonical_company_id, d);
        });

        if (isMounted && Array.isArray(realResults) && realResults.length > 0) {
          const mapped = realResults.map((r) => {
            const compId = r.canonical_company_id || r.id;
            const existingDec = decisionMap.get(compId);
            return {
            id: r.canonical_company_id || r.id,
            rank: r.rank,
            name: r.company_name,
            ticker: r.ticker,
            country: r.country,
            exchange: r.exchange,
            sector: r.sector,
            score: r.score,
            displayPrice: r.display_price,
            fwdPe: r.fwd_pe,
            peg: r.peg,
            evEbitda: r.ev_ebitda,
            beta: r.beta,
            ndEbitda: r.nd_ebitda,
            yieldPct: r.yield_pct,
            epsGrowthPct: r.eps_growth_pct,
            peVsBenchmark: r.pe_vs_benchmark,
            priceToSales: r.price_to_sales,
            priceToCashFlow: r.price_to_cash_flow,
            revenueGrowthFwd: r.revenue_growth_fwd,
            avgDailyVolume: r.avg_daily_volume,
            avgDailyTradedValue: r.avg_daily_traded_value,
            dataConfidence: r.data_confidence || 'High',
            marketCapDisplay: r.market_cap_display,
            marketCapCategory: (r.market_cap_display && r.market_cap_display >= 10e9) ? 'Large-cap Quality' : ((r.market_cap_display && r.market_cap_display >= 2e9) ? 'Mid-cap Value' : 'Small-cap Growth'),
            stageStatus: r.stage_status || 'passed',
            nearMissStatus: r.near_miss_status || 'none',
            deltaStatus: r.stage_status === 'passed' ? 'retained' : 'exited',
            movementReason: r.metric_statuses?.diversification || (r.near_miss_status !== 'none' ? (r.near_miss_status === 'rank_near_miss' ? 'Rank Near-Miss' : 'Rule Near-Miss') : ''),
            decision: existingDec?.decision || r.decision || 'pending',
            decisionReason: existingDec?.decision_reason || r.metric_statuses?.diversification || r.decision_reason || '',
            decisionNote: existingDec?.decision_note || r.decision_note || '',
            scoreBreakdown: r.score_breakdown || [],
            metricStatuses: r.metric_statuses || {},
          };
          });
          setSecurities(mapped);
          return;
        }
      } catch (err) {
        console.warn('[ScreeningContext] Could not load results for run:', selectedRunId, err);
      }

      if (isMounted) {
        setSecurities([]);
      }
    }

    loadResults();

    // 3. Attempt to fetch real backend comparison if compareRunId is set
    if (compareRunId && compareRunId !== 'none') {
      fetchRunComparison(selectedRunId, compareRunId)
        .then((comp) => {
          if (isMounted && comp && comp.rule_diffs) {
            setBackendRunComparison(comp);
          }
        })
        .catch(() => {});
    }

    return () => {
      isMounted = false;
    };
  }, [selectedRunId, compareRunId]);

  // Persistent workspace states across browser refreshes
  const [sectorLimits, setSectorLimits] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_active_sector_limits');
      return cached ? JSON.parse(cached) : INITIAL_SECTOR_LIMITS;
    } catch {
      return INITIAL_SECTOR_LIMITS;
    }
  });

  const [sectors, setSectors] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_active_sectors');
      return cached ? JSON.parse(cached) : INITIAL_SECTORS;
    } catch {
      return INITIAL_SECTORS;
    }
  });

  const [countries, setCountries] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_active_countries');
      return cached ? JSON.parse(cached) : INITIAL_COUNTRIES;
    } catch {
      return INITIAL_COUNTRIES;
    }
  });

  const [exchanges, setExchanges] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_active_exchanges');
      return cached ? JSON.parse(cached) : INITIAL_EXCHANGES;
    } catch {
      return INITIAL_EXCHANGES;
    }
  });

  const [diversification, setDiversification] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_active_diversification');
      return cached ? JSON.parse(cached) : INITIAL_DIVERSIFICATION;
    } catch {
      return INITIAL_DIVERSIFICATION;
    }
  });

  const [ruleMetrics, setRuleMetrics] = useState(createDefaultRuleMetrics);

  // Profiles and Version History with instant LocalStorage hydration & Backend sync
  const [profiles, setProfiles] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_profiles_cache');
      if (!cached) return [];
      const parsed = JSON.parse(cached);
      return Array.isArray(parsed)
        ? parsed.filter((p) => p && p.name && p.id !== '1' && p.id !== '2' && p.id !== '3' && p.id !== '4')
        : [];
    } catch {
      return [];
    }
  });

  const [versionHistory, setVersionHistory] = useState(() => {
    try {
      const cached = localStorage.getItem('screening_history_cache');
      if (!cached) return [];
      const parsed = JSON.parse(cached);
      return Array.isArray(parsed)
        ? parsed.filter((v) => v && v.name && v.id !== '1' && v.id !== '2' && v.id !== '3' && v.id !== '4')
        : [];
    } catch {
      return [];
    }
  });

  const [editingVersion, setEditingVersion] = useState(null);
  const activeProfile = profiles.find((profile) => profile.badge === 'Active');
  const currentRun = runHistory.find((r) => r.id === selectedRunId) || runHistory[0] || null;

  const selectedSecurity = securities.find((s) => s.id === selectedSecurityId) || null;
  const selectedSectorNames = sectors.filter((sector) => sector.selected).map((sector) => sector.name);

  // Sync workspace rule state to localStorage only when actively editing a version; otherwise clear it
  useEffect(() => {
    try {
      if (editingVersion) {
        localStorage.setItem('screening_active_rule_metrics', JSON.stringify(ruleMetrics));
      } else {
        localStorage.removeItem('screening_active_rule_metrics');
      }
    } catch {}
  }, [ruleMetrics, editingVersion]);

  useEffect(() => {
    try {
      localStorage.setItem('screening_active_sector_limits', JSON.stringify(sectorLimits));
    } catch {}
  }, [sectorLimits]);

  useEffect(() => {
    try {
      localStorage.setItem('screening_active_countries', JSON.stringify(countries));
    } catch {}
  }, [countries]);

  useEffect(() => {
    try {
      localStorage.setItem('screening_active_exchanges', JSON.stringify(exchanges));
    } catch {}
  }, [exchanges]);

  useEffect(() => {
    try {
      localStorage.setItem('screening_active_sectors', JSON.stringify(sectors));
    } catch {}
  }, [sectors]);

  useEffect(() => {
    try {
      localStorage.setItem('screening_active_diversification', JSON.stringify(diversification));
    } catch {}
  }, [diversification]);

  // Load authoritative profiles from PostgreSQL backend on mount, safely merging with local storage
  useEffect(() => {
    let isMounted = true;

    async function loadBackendProfiles() {
      try {
        // Step 1: Read whatever is currently in local storage
        let localProfiles = [];
        try {
          const cachedProfilesStr = localStorage.getItem('screening_profiles_cache');
          if (cachedProfilesStr) {
            const parsed = JSON.parse(cachedProfilesStr);
            if (Array.isArray(parsed)) {
              localProfiles = parsed.filter(
                (p) => p && p.name && p.id !== '1' && p.id !== '2' && p.id !== '3' && p.id !== '4'
              );
            }
          }
        } catch {}

        let localHistory = [];
        try {
          const cachedHistoryStr = localStorage.getItem('screening_history_cache');
          if (cachedHistoryStr) {
            const parsed = JSON.parse(cachedHistoryStr);
            if (Array.isArray(parsed)) {
              localHistory = parsed.filter(
                (v) => v && v.name && v.id !== '1' && v.id !== '2' && v.id !== '3' && v.id !== '4'
              );
            }
          }
        } catch {}

        // Step 2: Query PostgreSQL backend
        const backendProfiles = await fetchProfilesApi();
        if (!isMounted) return;

        if (backendProfiles && Array.isArray(backendProfiles)) {
          const realBackendProfiles = backendProfiles.filter(
            (bp) => bp && bp.profile_name && bp.version_id !== '1' && bp.version_id !== '2'
          );

          const { parsedProfiles, parsedHistory } = mapBackendProfilesToFrontend(realBackendProfiles);

          // Build index of backend IDs and profile keys
          const backendIds = new Set(parsedProfiles.map((p) => p.id));
          const backendProfileKeys = new Set(parsedProfiles.map((p) => p.profileKey));

          // Keep any locally created profiles that are not yet in backend
          const unsyncedProfiles = localProfiles.filter(
            (lp) => !backendIds.has(lp.id) && !backendProfileKeys.has(lp.profileKey)
          );
          const unsyncedHistory = localHistory.filter(
            (lh) => !backendIds.has(lh.id)
          );

          const combinedProfiles = [...parsedProfiles, ...unsyncedProfiles];
          const combinedHistory = [...parsedHistory, ...unsyncedHistory];

          if (combinedProfiles.length > 0 && !combinedProfiles.some((p) => p.badge === 'Active')) {
            combinedProfiles[0].badge = 'Active';
          }

          setProfiles(combinedProfiles);
          setVersionHistory(combinedHistory);

          try {
            localStorage.setItem('screening_profiles_cache', JSON.stringify(combinedProfiles));
            localStorage.setItem('screening_history_cache', JSON.stringify(combinedHistory));
          } catch {}

          const active = combinedProfiles.find((p) => p.badge === 'Active') || combinedProfiles[0];
          if (active) {
            setSelectedProfileName(`${active.name} - Version ${active.versionNumber}`);
          }

          // Step 3: Background auto-sync unsynced local profiles to backend if backend is available
          if (unsyncedProfiles.length > 0) {
            for (const unsynced of unsyncedProfiles) {
              try {
                const sectorLimitsMap = {};
                (unsynced.snapshot?.sectorLimits || []).forEach((item) => {
                  if (item.limit !== '' && !isNaN(parseFloat(item.limit))) {
                    sectorLimitsMap[item.sector] = parseFloat(item.limit);
                  }
                });

                const activeRules = (unsynced.snapshot?.metrics || [])
                  .filter((m) => m.mode !== 'Off' && m.value !== '' && parseProfileRuleValue(m.value) !== null)
                  .map((m) => ({
                    id: CANONICAL_METRIC_IDS[m.name] || m.name.toLowerCase().replace(/[^a-z0-9]+/g, '_'),
                    name: m.name,
                    category: m.category || 'Valuation',
                    mode: m.mode || 'Both',
                    condition: m.condition || '>=',
                    value: parseProfileRuleValue(m.value) || 0.0,
                    value_display: `${m.condition || ''} ${m.value || ''}`.trim(),
                    weight: m.mode === 'Off' || m.mode === 'Req.' ? 0.0 : (parseFloat(m.weight) || 0.0),
                  }));

                await createProfileApi({
                  profile_name: unsynced.name,
                  version_number: String(unsynced.versionNumber || 1),
                  description: unsynced.description || `Saved screening rules (Version ${unsynced.versionNumber || 1})`,
                  is_active: unsynced.badge === 'Active',
                  sector_limits: sectorLimitsMap,
                  diversification_rules: {
                    ...unsynced.snapshot?.diversification,
                    snapshot: unsynced.snapshot,
                  },
                  changes: unsynced.changes || [],
                  rules: activeRules,
                });
              } catch (syncErr) {
                console.warn('[ScreeningContext] Could not auto-sync local profile to backend:', unsynced.name, syncErr);
              }
            }
          }
        } else {
          // Backend is offline or returned null/error
          // Guarantee that local profiles and history are NEVER wiped!
          if (localProfiles.length > 0) {
            setProfiles(localProfiles);
            setVersionHistory(localHistory);
            const active = localProfiles.find((p) => p.badge === 'Active') || localProfiles[0];
            if (active) {
              setSelectedProfileName(`${active.name} - Version ${active.versionNumber}`);
            }
          }
        }
      } catch (err) {
        console.warn('[ScreeningContext] Error loading profiles from backend:', err);
      }
    }

    loadBackendProfiles();
    loadRunHistory();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (filterSector !== 'All' && !selectedSectorNames.includes(filterSector)) {
      setFilterSector('All');
    }
  }, [filterSector, selectedSectorNames.join('|')]);

  const setSecurityDecision = (id, decision, reason, note) => {
    let targetSec = null;
    setSecurities((prev) =>
      prev.map((sec) => {
        if (sec.id === id) {
          targetSec = {
            ...sec,
            decision,
            decisionReason: reason !== undefined ? reason : sec.decisionReason,
            decisionNote: note !== undefined ? note : sec.decisionNote,
          };
          return targetSec;
        }
        return sec;
      })
    );

    // Phase 16: Persist analyst decision to PostgreSQL with company_name and profile_name
    if (targetSec) {
      const activeProfName =
        currentRun?.rules ||
        (activeProfile
          ? `${activeProfile.name}${activeProfile.versionNumber ? ` v${activeProfile.versionNumber}` : ''}`
          : 'Core Strategy');

      recordDecisionApi({
        canonical_company_id: targetSec.id || id,
        company_name: targetSec.name,
        profile_name: activeProfName,
        decision,
        decision_reason: reason !== undefined ? reason : targetSec.decisionReason,
        decision_note: note !== undefined ? note : targetSec.decisionNote,
        run_id: selectedRunId,
      }).catch((err) => {
        console.warn('[ScreeningContext] Could not persist decision to backend:', err);
      });
    }
  };

  const toggleSector = (name) => {
    setSectors((prev) =>
      prev.map((sector) => (sector.name === name ? { ...sector, selected: !sector.selected } : sector))
    );
  };

  const setAllSectors = (selected) => {
    setSectors((prev) => prev.map((sector) => ({ ...sector, selected })));
  };

  const updateScheduleConfig = (updates) => {
    setScheduleConfig((prev) => ({ ...prev, ...updates }));
  };

    const loadRunHistory = async () => {
    try {
      const runs = await fetchScreeningRuns(50);
      if (runs && Array.isArray(runs)) {
        if (runs.length === 0) {
          setRunHistory([]);
          setSelectedRunId(null);
          setSecurities([]);
          return;
        }

        const mapped = runs.map((r) => {
          const startedDate = r.started_at ? new Date(r.started_at) : null;
          const startedStr = startedDate
            ? startedDate.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) +
              ', ' +
              startedDate.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
            : 'Just now';

          const durationStr = r.duration_ms
            ? (r.duration_ms >= 1000 ? `${(r.duration_ms / 1000).toFixed(1)}s` : `${Math.round(r.duration_ms)}ms`)
            : (r.status === 'running' ? 'In progress...' : '0ms');

          // Auto-append version tag if not already part of profile_name
          let displayRulesName = r.profile_name || 'Custom Strategy';
          if (r.rule_version_id && !displayRulesName.toLowerCase().includes('version') && !displayRulesName.toLowerCase().includes('v1') && !displayRulesName.toLowerCase().includes('v2')) {
            const matched = versionHistory.find((v) => v.id === r.rule_version_id) || profiles.find((p) => p.id === r.rule_version_id);
            if (matched && matched.versionNumber) {
              displayRulesName = `${displayRulesName} - Version ${matched.versionNumber}`;
            }
          }

          return {
            id: r.run_id,
            run: r.run_id,
            started: startedStr,
            rawStarted: r.started_at,
            rules: displayRulesName,
            rule_version_id: r.rule_version_id,
            screened: r.status === 'running' ? 'Evaluating...' : (r.universe_count || 0),
            selected: r.status === 'running' ? '—' : (r.selected_count || 0),
            status: r.status === 'succeeded' ? 'Succeeded' : (r.status === 'running' ? 'Running' : 'Failed'),
            duration: durationStr,
            duration_ms: r.duration_ms,
            countries: r.selected_countries || [],
            exchanges: r.selected_exchanges || [],
          };
        });
        setRunHistory(mapped);
        setSelectedRunId((prev) => {
          const exists = mapped.some((item) => item.id === prev);
          return exists ? prev : mapped[0].id;
        });
      }
    } catch (err) {
      console.warn('[ScreeningContext] Could not load run history from backend:', err);
      setRunHistory([]);
      setSelectedRunId(null);
      setSecurities([]);
    }
  };

  const triggerRunNow = async (profileIdToRun) => {
    setIsScreeningRunning(true);
    setScreeningError(null);
    setScreeningRunSuccess(null);

    const targetProfile = profiles.find((p) => p.id === profileIdToRun);
    if (!targetProfile) {
      setIsScreeningRunning(false);
      throw new Error('Please select a profile first before running.');
    }

    // Prepend in-progress run record so the user immediately sees progress in Run History table
    const tempRunId = `run-${new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 14)}`;
    const inProgressItem = {
      id: tempRunId,
      run: tempRunId,
      started: 'Just now',
      rules: `${targetProfile.name} - Version ${targetProfile.versionNumber || '1.0'}`,
      screened: 'Evaluating...',
      selected: '—',
      status: 'Running',
      duration: 'In progress...',
    };
    setRunHistory((prev) => [inProgressItem, ...prev]);

    try {
      // Resolve countries & exchanges from the selected profile's snapshot first!
      const profileSnapshot = targetProfile?.snapshot || targetProfile?.diversification_rules?.snapshot;

      let targetExchanges = [];
      if (profileSnapshot?.exchanges && Array.isArray(profileSnapshot.exchanges)) {
        targetExchanges = profileSnapshot.exchanges.filter((e) => e.selected).map((e) => e.id.toLowerCase());
      }
      if (targetExchanges.length === 0) {
        targetExchanges = exchanges.filter((e) => e.selected).map((e) => e.id.toLowerCase());
      }
      if (targetExchanges.length === 0) {
        targetExchanges = ['nse'];
      }

      let targetCountries = [];
      if (profileSnapshot?.countries && Array.isArray(profileSnapshot.countries)) {
        targetCountries = profileSnapshot.countries.filter((c) => c.selected).map((c) => c.id.toLowerCase());
      }
      if (targetCountries.length === 0) {
        targetCountries = countries.filter((c) => c.selected).map((c) => c.id.toLowerCase());
      }
      if (targetCountries.length === 0) {
        targetCountries = ['in'];
      }

      const payload = {
        countries: targetCountries,
        exchanges: targetExchanges,
        rule_version_id: targetProfile.id,
        profile_name: `${targetProfile.name} - Version ${targetProfile.versionNumber || '1.0'}`,
        display_currency: 'USD',
      };

      console.log('[ScreeningContext] Triggering instant run with profile:', payload);
      const response = await initiateScreening(payload);

      if (response && response.run_id) {
        setScreeningRunSuccess({
          runId: response.run_id,
          durationMs: response.duration_ms,
          screenedCount: response.funnel?.universe || 0,
          selectedCount: response.funnel?.selected || 0,
        });

        // Update funnel counts in UI
        if (response.funnel) {
          setFunnelState((prev) => ({
            ...prev,
            counts: {
              universe: response.funnel.universe,
              markets: response.funnel.markets,
              floors: response.funnel.floors,
              gates: response.funnel.gates,
              score: response.funnel.score,
              shortlist: response.funnel.shortlist,
              selected: response.funnel.selected,
            },
            runInfo: {
              ...prev.runInfo,
              asOfDate: `Run ${response.run_id} completed`,
            },
          }));
        }

        // Refresh runs list from PostgreSQL and set active run
        await loadRunHistory();
        setSelectedRunId(response.run_id);
        return response;
      }
    } catch (err) {
      console.error('[ScreeningContext] Instant run failed:', err);
      setScreeningError(err.message || 'Screening execution failed');
      // Remove temporary in-progress item on failure
      setRunHistory((prev) => prev.filter((r) => r.id !== tempRunId));
      throw err;
    } finally {
      setIsScreeningRunning(false);
    }
  };

const loadConfiguration = (snapshot, navigateToCatalog = true) => {
    if (!snapshot) return;
    const metrics = (snapshot.metrics || []).map((metric) => ({ ...metric }));
    const limits = (snapshot.sectorLimits || []).map((item) => ({ ...item }));
    const c = (snapshot.countries || INITIAL_COUNTRIES).map((country) => ({ ...country }));
    const ex = (snapshot.exchanges || INITIAL_EXCHANGES).map((exchange) => ({ ...exchange }));
    const sec = (snapshot.sectors || INITIAL_SECTORS).map((sector) => ({ ...sector }));
    const div = { ...(snapshot.diversification || INITIAL_DIVERSIFICATION) };

    setRuleMetrics(metrics);
    setSectorLimits(limits);
    setCountries(c);
    setExchanges(ex);
    setSectors(sec);
    setDiversification(div);

    try {
      localStorage.setItem('screening_active_rule_metrics', JSON.stringify(metrics));
      localStorage.setItem('screening_active_sector_limits', JSON.stringify(limits));
      localStorage.setItem('screening_active_countries', JSON.stringify(c));
      localStorage.setItem('screening_active_exchanges', JSON.stringify(ex));
      localStorage.setItem('screening_active_sectors', JSON.stringify(sec));
      localStorage.setItem('screening_active_diversification', JSON.stringify(div));
    } catch {}

    if (navigateToCatalog) {
      setRulesTab('configuration');
    }
  };

  const activateProfile = async (id) => {
    const target = profiles.find((p) => p.id === id);
    if (target) {
      try {
        await activateProfileApi(id);
      } catch (err) {
        console.warn('[ScreeningContext] Backend activation sync skipped:', err);
      }

      setProfiles((prev) => {
        const updated = prev.map((profile) => ({
          ...profile,
          badge: profile.id === id ? 'Active' : profile.badge === 'Active' ? 'Saved' : profile.badge,
        }));
        try {
          localStorage.setItem('screening_profiles_cache', JSON.stringify(updated));
        } catch {}
        return updated;
      });

      setVersionHistory((prev) => {
        const updated = prev.map((item) => ({
          ...item,
          isCurrent:
            item.profileKey === target.profileKey &&
            item.versionNumber === target.versionNumber,
        }));
        try {
          localStorage.setItem('screening_history_cache', JSON.stringify(updated));
        } catch {}
        return updated;
      });

      setSelectedProfileName(`${target.name} - Version ${target.versionNumber}`);
    }
  };

  const restoreVersion = async (version) => {
    const target = versionHistory.find(
      (item) => item.id === version || item.version === version
    );
    if (target) {
      if (target.id && !target.id.includes('-v')) {
        try {
          await activateProfileApi(target.id);
        } catch (err) {
          console.warn('[ScreeningContext] Backend restore sync skipped:', err);
        }
      }
      setProfiles((prev) => {
        const updated = prev.map((profile) => ({
          ...profile,
          badge:
            profile.profileKey === target.profileKey &&
            profile.versionNumber === target.versionNumber
              ? 'Active'
              : profile.badge === 'Active'
                ? 'Saved'
                : profile.badge,
        }));
        try {
          localStorage.setItem('screening_profiles_cache', JSON.stringify(updated));
        } catch {}
        return updated;
      });
      setVersionHistory((prev) => {
        const updated = prev.map((v) => ({
          ...v,
          isCurrent: v.id === version || v.version === version,
        }));
        try {
          localStorage.setItem('screening_history_cache', JSON.stringify(updated));
        } catch {}
        return updated;
      });
      if (target.snapshot) {
        loadConfiguration(target.snapshot, false);
      }
      setSelectedProfileName(`${target.name || 'Saved profile'} - Version ${target.versionNumber}`);
    }
  };

  const updateSectorLimit = (sector, newLimit) => {
    setSectorLimits((prev) =>
      prev.map((item) => (item.sector === sector ? { ...item, limit: newLimit } : item))
    );
  };

  const updateSectorNote = (sector, note) => {
    setSectorLimits((prev) =>
      prev.map((item) => (item.sector === sector ? { ...item, note } : item))
    );
  };

  const toggleCountry = (id) => {
    setCountries((prev) =>
      prev.map((country) => (country.id === id ? { ...country, selected: !country.selected } : country))
    );
    setExchanges((prev) =>
      prev.map((exchange) =>
        exchange.countryId === id && countries.find((country) => country.id === id)?.selected
          ? { ...exchange, selected: false }
          : exchange
      )
    );
  };

  const toggleExchange = (id) => {
    setExchanges((prev) =>
      prev.map((exchange) => (exchange.id === id ? { ...exchange, selected: !exchange.selected } : exchange))
    );
  };

  const updateDiversification = (updates) => {
    setDiversification((prev) => ({ ...prev, ...updates }));
  };

  const updateRuleMetric = (metricName, updates) => {
    setRuleMetrics((prev) =>
      prev.map((metric) => {
        if (metric.name !== metricName) return metric;
        const next = { ...metric, ...updates };
        // Mode & Weight validation:
        // When mode is Off or Req (Gate only), weight is locked to 0
        if (next.mode === 'Off' || next.mode === 'Req.') {
          next.weight = 0;
        } else if ((next.mode === 'Score' || next.mode === 'Both') && (next.weight === 0 || next.weight === undefined)) {
          // When switching to Score or Both and weight was 0, default to 10
          next.weight = 10;
        }
        return next;
      })
    );
  };

  const autoBalanceWeights = () => {
    setRuleMetrics((prev) => {
      const scoringMetrics = prev.filter((m) => m.mode === 'Score' || m.mode === 'Both');
      if (scoringMetrics.length === 0) return prev;
      const currentTotal = scoringMetrics.reduce((sum, m) => sum + (Number(m.weight) || 0), 0);

      return prev.map((m) => {
        if (m.mode !== 'Score' && m.mode !== 'Both') {
          return { ...m, weight: 0 };
        }
        let target;
        if (currentTotal > 0) {
          target = Math.round(((Number(m.weight) || 0) / currentTotal) * 100);
        } else {
          target = Math.round(100 / scoringMetrics.length);
        }
        return { ...m, weight: Math.min(100, Math.max(0, target)) };
      });
    });
  };

  const saveConfigurationAsNewVersion = async (name, configuration, profileKey = null, editedFromVersion = null) => {
    const trimmedName = name.trim();
    if (!trimmedName) return { saved: false, error: 'Name is required' };

    const snapshot = configuration || {
      metrics: ruleMetrics.map((metric) => ({ ...metric })),
      sectorLimits: sectorLimits.map((item) => ({ ...item })),
      countries: countries.map((country) => ({ ...country })),
      exchanges: exchanges.map((exchange) => ({ ...exchange })),
      sectors: sectors.map((sector) => ({ ...sector })),
      diversification: { ...diversification },
    };

    const cleanSlug = trimmedName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
    const existingProfile = profiles.find(
      (profile) => profile.name.trim().toLowerCase() === trimmedName.toLowerCase() || profile.profileKey === cleanSlug
    );
    const nextProfileKey = profileKey || existingProfile?.profileKey || cleanSlug;
    const nextVersionNumber =
      Math.max(
        ...profiles
          .filter((profile) => profile.profileKey === nextProfileKey)
          .map((profile) => profile.versionNumber || 0),
        ...versionHistory
          .filter((item) => item.profileKey === nextProfileKey)
          .map((item) => item.versionNumber || 0),
        0
      ) + 1;
    const version = `v${nextVersionNumber}`;

    // Format for backend PostgreSQL persistence
    const sectorLimitsMap = {};
    (snapshot.sectorLimits || []).forEach((item) => {
      if (item.limit !== '' && !isNaN(parseFloat(item.limit))) {
        sectorLimitsMap[item.sector] = parseFloat(item.limit);
      }
    });

    const activeRulesForBackend = (snapshot.metrics || [])
      .filter((m) => m.mode !== 'Off' && m.value !== '' && parseProfileRuleValue(m.value) !== null)
      .map((m) => {
        const canonicalId = CANONICAL_METRIC_IDS[m.name] || m.name.toLowerCase().replace(/[^a-z0-9]+/g, '_');
        const numVal = parseProfileRuleValue(m.value) || 0.0;
        return {
          id: canonicalId,
          name: m.name,
          category: m.category || 'Valuation',
          mode: m.mode || 'Both',
          condition: m.condition || '>=',
          value: numVal,
          value_display: `${m.condition || ''} ${m.value || ''}`.trim(),
          weight: m.mode === 'Off' || m.mode === 'Req.' ? 0.0 : (parseFloat(m.weight) || 0.0),
        };
      });

    // Find previous snapshot to compute comparison changes from previous version
    let prevSnapshot = null;
    if (editedFromVersion) {
      const match =
        versionHistory.find((v) => v.profileKey === nextProfileKey && v.versionNumber === editedFromVersion) ||
        profiles.find((p) => p.profileKey === nextProfileKey && p.versionNumber === editedFromVersion);
      prevSnapshot = match?.snapshot || null;
    } else {
      const existingVersions = versionHistory
        .filter((v) => v.profileKey === nextProfileKey)
        .sort((a, b) => (b.versionNumber || 0) - (a.versionNumber || 0));
      prevSnapshot = existingVersions[0]?.snapshot || existingProfile?.snapshot || null;
    }

    const comparisonDiff = computeProfileVersionDiff(snapshot, prevSnapshot);
    const changeSummaryText = prevSnapshot
      ? `${comparisonDiff.length} change${comparisonDiff.length === 1 ? '' : 's'} compared to Version ${editedFromVersion || (nextVersionNumber - 1)}`
      : `Initial profile created with ${activeRulesForBackend.length} active rules`;

    const selectedCountries = (snapshot.countries || [])
      .filter((c) => c.selected)
      .map((c) => c.name);

    const backendPayload = {
      profile_name: trimmedName,
      version_number: String(nextVersionNumber),
      description: `Saved screening rules (Version ${nextVersionNumber})`,
      is_active: true,
      sector_limits: sectorLimitsMap,
      diversification_rules: {
        ...snapshot.diversification,
        snapshot,
      },
      changes: comparisonDiff,
      selected_countries: selectedCountries,
      rules: activeRulesForBackend,
    };

    let backendVersionId = `${nextProfileKey}-${version}`;
    try {
      const createdBackend = await createProfileApi(backendPayload);
      if (createdBackend?.version_id) {
        backendVersionId = createdBackend.version_id;
      }
    } catch (err) {
      console.warn('[ScreeningContext] Could not persist profile to backend, using local store:', err);
    }

    const newHistoryItem = {
      id: backendVersionId,
      profileKey: nextProfileKey,
      versionNumber: nextVersionNumber,
      version,
      isCurrent: true,
      date: new Date().toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      }),
      by: 'PM',
      name: trimmedName,
      editedFromVersion,
      changeSummary: changeSummaryText,
      resultImpact: '-',
      changes: comparisonDiff,
      selectedCountries,
      snapshot,
    };

    const newProfileItem = {
      id: backendVersionId,
      profileKey: nextProfileKey,
      name: trimmedName,
      badge: 'Active',
      description: `Saved screening rules (Version ${nextVersionNumber})`,
      version,
      versionNumber: nextVersionNumber,
      changes: comparisonDiff,
      selectedCountries,
      snapshot,
    };

    setVersionHistory((prev) => {
      const updated = [newHistoryItem, ...prev.map((item) => ({ ...item, isCurrent: false }))];
      try {
        localStorage.setItem('screening_history_cache', JSON.stringify(updated));
      } catch {}
      return updated;
    });

    setProfiles((prev) => {
      // Remove any previous entry with the exact same version id if present
      const remaining = prev.filter((p) => p.id !== backendVersionId);
      const updated = [
        newProfileItem,
        ...remaining.map((profile) => ({
          ...profile,
          badge: profile.badge === 'Active' ? 'Saved' : profile.badge,
        })),
      ];
      try {
        localStorage.setItem('screening_profiles_cache', JSON.stringify(updated));
      } catch {}
      return updated;
    });

    setSelectedProfileName(`${trimmedName} - ${version}`);
    return { saved: true, version };
  };

  const deleteVersion = async (versionId) => {
    const target = versionHistory.find(
      (item) => item.id === versionId || item.version === versionId
    );
    if (!target) return false;

    try {
      await deleteProfileApi(target.id);
    } catch (err) {
      console.warn('[ScreeningContext] Backend delete sync skipped:', err);
    }

    const remainingHistory = versionHistory.filter((item) => item.id !== target.id);
    const profileVersions = remainingHistory
      .filter((item) => item.profileKey === target.profileKey)
      .sort((left, right) => (right.versionNumber || 0) - (left.versionNumber || 0));
    const replacement = profileVersions.find((item) => item.isCurrent) || profileVersions[0];

    const updatedHistory = remainingHistory.map((item) => ({
      ...item,
      isCurrent: item.profileKey === target.profileKey
        ? Boolean(replacement && item.id === replacement.id)
        : item.isCurrent,
    }));
    setVersionHistory(updatedHistory);
    try {
      localStorage.setItem('screening_history_cache', JSON.stringify(updatedHistory));
    } catch {}

    setProfiles((prev) => {
      const remainingProfiles = prev.filter((profile) => profile.id !== target.id);
      let updatedProfiles;
      if (!replacement) {
        updatedProfiles = remainingProfiles;
      } else {
        updatedProfiles = remainingProfiles.map((profile) => (
          profile.profileKey === target.profileKey
            ? {
                ...profile,
                badge: profile.id === replacement.id ? 'Active' : 'Saved',
              }
            : profile
        ));
      }
      try {
        localStorage.setItem('screening_profiles_cache', JSON.stringify(updatedProfiles));
      } catch {}
      return updatedProfiles;
    });

    return true;
  };

  const beginVersionEdit = (versionId) => {
    const target =
      versionHistory.find((item) => item.id === versionId || item.version === versionId) ||
      profiles.find((item) => item.id === versionId || item.version === versionId);
    if (!target?.snapshot) {
      console.warn('[ScreeningContext] Could not find profile snapshot for versionId:', versionId);
      return;
    }

    loadConfiguration(target.snapshot, true);
    setEditingVersion({
      id: target.id || target.version,
      name: target.name || 'Saved profile',
      profileKey: target.profileKey,
      versionNumber: target.versionNumber,
    });
    setRulesTab('configuration');
  };

  const saveAsNewVersion = (name) => saveConfigurationAsNewVersion(name);

  const discardChanges = () => {
    setRuleMetrics(createDefaultRuleMetrics());
    setSectorLimits(INITIAL_SECTOR_LIMITS.map((item) => ({ ...item })));
    setSectors(INITIAL_SECTORS.map((sector) => ({ ...sector })));
    setCountries(INITIAL_COUNTRIES.map((country) => ({ ...country })));
    setExchanges(INITIAL_EXCHANGES.map((exchange) => ({ ...exchange })));
    setDiversification({ ...INITIAL_DIVERSIFICATION });
    setEditingVersion(null);

    try {
      localStorage.removeItem('screening_active_rule_metrics');
      localStorage.removeItem('screening_active_sector_limits');
      localStorage.removeItem('screening_active_countries');
      localStorage.removeItem('screening_active_exchanges');
      localStorage.removeItem('screening_active_sectors');
      localStorage.removeItem('screening_active_diversification');
    } catch {}
  };

  return (
    <ScreeningContext.Provider
      value={{
        activeNav,
        setActiveNav,
        rulesTab,
        setRulesTab,
        resultsTab,
        setResultsTab,
        selectedProfileName,
        draftProfileName,
        setDraftProfileName,
        selectedSecurity,
        selectedSecurityId,
        setSelectedSecurityId,
        securities,
        filterSector,
        setFilterSector,
        filterRegion,
        setFilterRegion,
        filterCap,
        setFilterCap,
        searchQuery,
        setSearchQuery,
        funnelState,
        setFunnelState,
        setSecurityDecision,
        scheduleConfig,
        updateScheduleConfig,
        runHistory,
        selectedRunId,
        setSelectedRunId,
        currentRun,
        compareRunId,
        setCompareRunId,
        triggerRunNow,
        loadRunHistory,
        isScreeningRunning,
        screeningError,
        screeningRunSuccess,
        setScreeningError,
        setScreeningRunSuccess,
        profiles,
        activeProfile,
        activateProfile,
        versionHistory,
        restoreVersion,
        editingVersion,
        setEditingVersion,
        beginVersionEdit,
        sectorLimits,
        updateSectorLimit,
        updateSectorNote,
        ruleMetrics,
        updateRuleMetric,
        autoBalanceWeights,
        saveAsNewVersion,
        saveConfigurationAsNewVersion,
        deleteVersion,
        discardChanges,
        loadConfiguration,
        countries,
        sectors,
        toggleCountry,
        exchanges,
        toggleExchange,
        toggleSector,
        setAllSectors,
        diversification,
        updateDiversification,
      }}
    >
      {children}
    </ScreeningContext.Provider>
  );
};

export const useScreening = () => {
  const context = useContext(ScreeningContext);
  if (!context) {
    throw new Error('useScreening must be used within a ScreeningProvider');
  }
  return context;
};
