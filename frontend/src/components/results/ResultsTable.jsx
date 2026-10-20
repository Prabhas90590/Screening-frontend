import React from 'react';
import { useScreening } from '../../context/ScreeningContext';
import { Badge } from '../common/Badge';

export const ResultsTable = ({ holdings, uploadedHoldingRows }) => {
  const {
    securities,
    sectors,
    sectorLimits,
    ruleMetrics,
    selectedSecurity,
    setSelectedSecurityId,
    setSecurityDecision,
    filterSector,
    filterRegion,
    filterCap,
    searchQuery,
    resultsTab,
  } = useScreening();

  const countryValueByResultCountry = {
    US: 'United States',
  };
  const selectedSectorNames = new Set(
    sectors.filter((sector) => sector.selected).map((sector) => sector.name)
  );
  const netDebtMetric = ruleMetrics.find((metric) => metric.name === 'Net debt / EBITDA');
  const generalDebtLimit = Number.parseFloat(netDebtMetric?.value);
  const sectorDebtLimits = new Map(
    sectorLimits
      .filter((item) => item.limit !== '')
      .map((item) => [item.sector, Number.parseFloat(item.limit)])
  );
  const parseDebtRatio = (value) => {
    if (value === 'net cash') return 0;
    const parsedValue = Number.parseFloat(value);
    return Number.isFinite(parsedValue) ? parsedValue : null;
  };

  // Filter logic
  const tabSecurities = resultsTab === 'myHoldings'
    ? holdings
    : resultsTab === 'top20'
      ? securities.filter((security) => security.rank >= 1 && security.rank <= 20)
      : resultsTab === 'rankNearMisses'
        ? securities.filter((security) => security.rank >= 21 && security.rank <= 40)
        : resultsTab === 'ruleNearMisses'
          ? securities.filter((security) =>
              Object.values(security.metricStatuses).some((status) => status === 'threshold' || status === 'miss')
            )
          : [];

  const filteredSecurities = tabSecurities.filter((sec) => {
    if (!selectedSectorNames.has(sec.sector)) return false;
    if (filterSector !== 'All' && sec.sector !== filterSector) return false;
    if (filterRegion !== 'All') {
      const resultCountry = countryValueByResultCountry[sec.country] || sec.country;
      if (resultCountry !== filterRegion) return false;
    }
    if (
      netDebtMetric?.mode !== 'Off' &&
      netDebtMetric?.condition === '<=' &&
      (Number.isFinite(generalDebtLimit) || sectorDebtLimits.has(sec.sector))
    ) {
      const debtLimit = sectorDebtLimits.has(sec.sector)
        ? sectorDebtLimits.get(sec.sector)
        : generalDebtLimit;
      const debtValue = parseDebtRatio(sec.ndEbitda);
      if (Number.isFinite(debtLimit) && (debtValue === null || debtValue > debtLimit)) {
        if (netDebtMetric.mode === 'Req.' || netDebtMetric.mode === 'Both') return false;
      }
    }
    if (filterCap !== 'All') {
      if (filterCap === 'Large' && !sec.marketCapCategory.toLowerCase().includes('large')) return false;
      if (filterCap === 'Mid' && !sec.marketCapCategory.toLowerCase().includes('mid')) return false;
      if (filterCap === 'Small' && !sec.marketCapCategory.toLowerCase().includes('small')) return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = sec.name.toLowerCase().includes(q);
      const matchTicker = sec.ticker.toLowerCase().includes(q);
      if (!matchName && !matchTicker) return false;
    }
    return true;
  });

  const getMetricClass = (status) => {
    switch (status) {
      case 'full':
        return 'text-[#146b63] font-semibold';
      case 'threshold':
        return 'text-amber-600 font-semibold';
      case 'miss':
        return 'text-red-600 font-semibold';
      default:
        return 'text-slate-700';
    }
  };

  const getDataConfidenceBadge = (confidence) => {
    switch (confidence) {
      case 'High':
        return <Badge variant="teal" size="xs">High</Badge>;
      case 'Medium':
        return <Badge variant="amber" size="xs">Medium</Badge>;
      case 'Low':
        return <Badge variant="red" size="xs">Low</Badge>;
      default:
        return <Badge size="xs">{confidence}</Badge>;
    }
  };

  const emptyStateByTab = {
    top20: {
      title: 'No top 20 results',
      description: 'The top 20 companies from the current screening run will appear here.',
    },
    rankNearMisses: {
      title: 'No rank-based near misses',
      description: 'Companies ranked 21–40 will appear here when the current result set contains them.',
    },
    ruleNearMisses: {
      title: 'No rule-based near misses',
      description: 'Companies with threshold or missed metrics will appear here when available.',
    },
    myHoldings: {
      title: 'No holdings added',
      description: 'Upload a CSV with a ticker, symbol, security, or security_id column to see matching holdings.',
    },
    allScreened: {
      title: 'No screened companies yet',
      description: 'All companies fetched for the selected countries and exchanges will appear here after a backend screening run.',
    },
  };

  if (resultsTab === 'myHoldings' && uploadedHoldingRows.length > 0) {
    const columns = Object.keys(uploadedHoldingRows[0]);
    return (
      <div className="overflow-hidden rounded-lg border border-slate-200/80 bg-white shadow-2xs">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200/80 bg-slate-50/70 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                {columns.map((column) => (
                  <th key={column} className="whitespace-nowrap px-3 py-2.5">{column}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {uploadedHoldingRows.map((row, rowIndex) => (
                <tr key={`holding-${rowIndex}`} className="hover:bg-slate-50/80">
                  {columns.map((column) => (
                    <td key={`${rowIndex}-${column}`} className="whitespace-nowrap px-3 py-3 text-slate-700">
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

  if (filteredSecurities.length === 0) {
    const emptyState = emptyStateByTab[resultsTab] || emptyStateByTab.top20;
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
        <h2 className="text-sm font-semibold text-slate-800">{emptyState.title}</h2>
        <p className="mx-auto mt-2 max-w-xl text-xs leading-5 text-slate-500">
          {emptyState.description}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200/80 shadow-2xs overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-50/70 border-b border-slate-200/80 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <th className="py-2.5 px-3 w-8">#</th>
              <th className="py-2.5 px-3 min-w-[190px]">Security</th>
              <th className="py-2.5 px-3">Sector</th>
              <th className="py-2.5 px-3">Score</th>
              <th className="py-2.5 px-3">Fwd P/E</th>
              <th className="py-2.5 px-3">PEG</th>
              <th className="py-2.5 px-3">EV/EBITDA</th>
              <th className="py-2.5 px-3">Beta</th>
              <th className="py-2.5 px-3">ND/EBITDA</th>
              <th className="py-2.5 px-3">Yield</th>
              <th className="py-2.5 px-3">EPS Gr.</th>
              <th className="py-2.5 px-3">Data</th>
              <th className="py-2.5 px-3 text-center">Decision</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredSecurities.map((item) => {
              const isSelected = selectedSecurity?.id === item.id;
              return (
                <tr
                  key={item.id}
                  onClick={() => setSelectedSecurityId(item.id)}
                  className={`cursor-pointer transition-colors hover:bg-slate-50/80 ${
                    isSelected ? 'bg-teal-50/40 border-l-3 border-[#146b63]' : ''
                  }`}
                >
                  {/* Rank */}
                  <td className="py-3 px-3 text-slate-500 font-mono text-[11px]">
                    {item.rank}
                  </td>

                  {/* Security Name & Ticker */}
                  <td className="py-3 px-3">
                    <div className="font-semibold text-slate-900 leading-tight">
                      {item.name}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      {item.ticker} · {item.country}
                    </div>
                  </td>

                  {/* Sector */}
                  <td className="py-3 px-3 text-slate-700 whitespace-nowrap">
                    {item.sector}
                  </td>

                  {/* Score */}
                  <td className="py-3 px-3 font-bold text-slate-900 font-mono">
                    {item.score}
                  </td>

                  {/* FWD P/E */}
                  <td className={`py-3 px-3 font-mono ${getMetricClass(item.metricStatuses.fwdPe)}`}>
                    {item.fwdPe}
                  </td>

                  {/* PEG */}
                  <td className={`py-3 px-3 font-mono ${getMetricClass(item.metricStatuses.peg)}`}>
                    {item.peg}
                  </td>

                  {/* EV/EBITDA */}
                  <td className={`py-3 px-3 font-mono ${getMetricClass(item.metricStatuses.evEbitda)}`}>
                    {item.evEbitda > 0 ? item.evEbitda : 'n/a'}
                  </td>

                  {/* Beta */}
                  <td className={`py-3 px-3 font-mono ${getMetricClass(item.metricStatuses.beta)}`}>
                    {item.beta}
                  </td>

                  {/* ND/EBITDA */}
                  <td className={`py-3 px-3 font-mono ${getMetricClass(item.metricStatuses.ndEbitda)}`}>
                    {item.ndEbitda}
                  </td>

                  {/* Yield */}
                  <td className={`py-3 px-3 font-mono ${getMetricClass(item.metricStatuses.yield)}`}>
                    {item.yieldPct}%
                  </td>

                  {/* EPS Growth */}
                  <td className={`py-3 px-3 font-mono ${getMetricClass(item.metricStatuses.epsGrowth)}`}>
                    {item.epsGrowthPct}%
                  </td>

                  {/* Data Confidence */}
                  <td className="py-3 px-3 whitespace-nowrap">
                    {getDataConfidenceBadge(item.dataConfidence)}
                  </td>

                  {/* Decision Buttons */}
                  <td className="py-3 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                    <div className="inline-flex rounded-md shadow-2xs space-x-1">
                      <button
                        onClick={() => setSecurityDecision(item.id, 'keep')}
                        className={`px-2.5 py-1 text-[11px] font-semibold rounded transition-colors ${
                          item.decision === 'keep'
                            ? 'bg-[#146b63] text-white shadow-xs'
                            : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
                        }`}
                      >
                        Keep
                      </button>
                      <button
                        onClick={() => setSecurityDecision(item.id, 'drop')}
                        className={`px-2.5 py-1 text-[11px] font-semibold rounded transition-colors ${
                          item.decision === 'drop'
                            ? 'bg-rose-600 text-white shadow-xs'
                            : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
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
  );
};
