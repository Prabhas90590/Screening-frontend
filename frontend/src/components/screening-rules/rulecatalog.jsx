import React, { useMemo, useState } from 'react';
import { useScreening } from '../../context/ScreeningContext';

const categories = [
  'All metrics',
  'Size & liquidity',
  'Valuation',
  'Growth',
  'Risk & leverage',
  'Income',
  'Momentum',
  'Quality',
];

const conditions = [
  '>=',
  '<=',
  '=',
  '<',
  '>',
  'discount',
  'sector table',
];

const modes = ['Off', 'Req.', 'Score', 'Both'];

export const METRIC_LIMITS = {
  'Price (USD-equiv.)': { min: 0.50, max: 5000.0, display: '$0.50 – $5,000' },
  'Market cap (USD)': { min: 50_000_000, max: 4_000_000_000_000, display: '$50M – $4,000B' },
  'Avg daily volume (shares)': { min: 10_000, max: 500_000_000, display: '10K – 500M' },
  'Avg daily traded value (USD)': { min: 50_000, max: 5_000_000_000, display: '$50K – $5B' },
  'Forward P/E': { min: 1.0, max: 150.0, display: '1.0x – 150.0x' },
  'Forward P/E vs S&P 500': { min: -30.0, max: 60.0, display: '-30.0x – +60.0x' },
  'PEG': { min: 0.1, max: 5.0, display: '0.1x – 5.0x' },
  'EV / EBITDA': { min: 1.0, max: 60.0, display: '1.0x – 60.0x' },
  'Price / sales': { min: 0.1, max: 30.0, display: '0.1x – 30.0x' },
  'Price / cash flow': { min: 1.0, max: 50.0, display: '1.0x – 50.0x' },
  'Net debt / EBITDA': { min: -5.0, max: 15.0, display: '-5.0x – 15.0x' },
  'Beta': { min: 0.2, max: 3.0, display: '0.2x – 3.0x' },
  'EPS growth (5y, fwd)': { min: -20.0, max: 100.0, display: '-20% – 100%' },
  'Revenue growth (5y, fwd)': { min: -15.0, max: 80.0, display: '-15% – 80%' },
  'Dividend yield': { min: 0.0, max: 20.0, display: '0.0% – 20.0%' },
  '3y / 5y return': { min: -100.0, max: 1000.0, display: '-100% – +1,000%' },
  'Data confidence': { min: 1, max: 3, display: 'High / Med / Low' },
};

export const parseMetricNumeric = (raw) => {
  if (raw === '' || raw === undefined || raw === null) return null;
  const str = String(raw).trim().toLowerCase();
  if (str === 'high') return 3;
  if (str === 'medium' || str === 'med') return 2;
  if (str === 'low') return 1;

  const cleaned = str.replace(/[$,x%]/g, '').trim();
  if (!cleaned) return null;

  if (cleaned.endsWith('b')) {
    const n = parseFloat(cleaned.slice(0, -1));
    return isNaN(n) ? null : n * 1_000_000_000;
  }
  if (cleaned.endsWith('m')) {
    const n = parseFloat(cleaned.slice(0, -1));
    return isNaN(n) ? null : n * 1_000_000;
  }
  if (cleaned.endsWith('k')) {
    const n = parseFloat(cleaned.slice(0, -1));
    return isNaN(n) ? null : n * 1_000;
  }
  const n = parseFloat(cleaned);
  return isNaN(n) ? null : n;
};


export const RuleCatalog = () => {
  const {
    ruleMetrics,
    updateRuleMetric,
    autoBalanceWeights,
  } = useScreening();
  const [selectedCategory, setSelectedCategory] = useState('All metrics');

  const totalWeight = useMemo(
    () => ruleMetrics.reduce((total, metric) => total + metric.weight, 0),
    [ruleMetrics]
  );
  const visibleMetrics = useMemo(
    () =>
      selectedCategory === 'All metrics'
        ? ruleMetrics
        : ruleMetrics.filter((metric) => metric.category === selectedCategory),
    [ruleMetrics, selectedCategory]
  );

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-[120px_minmax(0,1fr)] overflow-hidden rounded-md border border-slate-300 bg-white">
        <aside className="border-r border-slate-200 bg-slate-50/70 p-1.5">
          <button
            onClick={() => setSelectedCategory('All metrics')}
            className={`mb-1 flex w-full items-center rounded px-2 py-1 text-left text-xs ${
              selectedCategory === 'All metrics'
                ? 'bg-[#e1f0ed] font-bold text-slate-800'
                : 'text-slate-700 hover:bg-slate-100'
            }`}
          >
            <span>All metrics</span>
          </button>
          <div className="space-y-0.5">
            {categories.slice(1).map((category) => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`flex w-full items-center rounded px-2 py-1 text-left text-xs ${
                  selectedCategory === category
                    ? 'bg-slate-200 font-semibold text-black'
                    : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                <span>{category}</span>
              </button>
            ))}
          </div>
          <button className="mt-2 rounded border border-slate-300 bg-white px-2 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-50">
            + Add metric
          </button>
        </aside>

        <section className="min-w-0 p-2">
          <div className="grid grid-cols-[minmax(140px,1.4fr)_176px_76px_minmax(105px,0.95fr)_65px_minmax(140px,1fr)] items-center gap-2 border-b border-slate-200 px-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
            <span>Metric</span>
            <span>Mode</span>
            <span>Cond.</span>
            <span>Value</span>
            <span>Full credit</span>
            <span>Weight</span>
          </div>

          <div>
            {visibleMetrics.length === 0 ? (
              <p className="px-2 py-8 text-center text-xs text-slate-500">
                No metrics are assigned to this category.
              </p>
            ) : visibleMetrics.map((metric) => {
              const limitSpec = METRIC_LIMITS[metric.name];
              const numericVal =
                limitSpec && metric.mode !== 'Off' && metric.value !== ''
                  ? parseMetricNumeric(metric.value)
                  : null;
              const isBeyondLimit =
                numericVal !== null &&
                (numericVal < limitSpec.min || numericVal > limitSpec.max);

              return (
              <div
                key={metric.name}
                className="grid grid-cols-[minmax(140px,1.4fr)_176px_76px_minmax(105px,0.95fr)_65px_minmax(140px,1fr)] items-center gap-2 border-b border-slate-100 px-2 py-1 text-[11px] last:border-b-0"
              >
                <div className="flex flex-col min-w-0">
                  <span className={`font-semibold ${metric.mode === 'Off' ? 'text-slate-400' : 'text-slate-800'}`}>
                    {metric.name}
                  </span>
                  {limitSpec && metric.mode !== 'Off' && (
                    <span className="text-[9px] text-slate-400 font-normal">
                      Range: {limitSpec.display}
                    </span>
                  )}
                </div>
                <div className="flex w-fit overflow-hidden rounded-md border border-slate-300 bg-slate-50">
                  {modes.map((mode) => (
                    <button
                      key={mode}
                      onClick={() => updateRuleMetric(metric.name, { mode })}
                      className={`px-2 py-1 text-[10px] font-semibold ${
                        metric.mode === mode
                          ? mode === 'Off'
                            ? 'bg-slate-400 text-white'
                            : 'bg-[#238c83] text-white'
                          : 'text-slate-500 hover:bg-white'
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
                <select
                  aria-label={`${metric.name} condition`}
                  value={metric.condition}
                  onChange={(event) => updateRuleMetric(metric.name, { condition: event.target.value })}
                  className="w-full min-w-0 rounded border border-slate-300 bg-white px-1 py-0.5 text-[11px] text-slate-600 outline-none focus:border-[#238c83] focus:text-black"
                >
                  <option value="">Select</option>
                  {conditions.map((condition) => (
                    <option key={condition} value={condition}>
                      {condition}
                    </option>
                  ))}
                </select>
                <div className="flex flex-col min-w-0">
                  <input
                    aria-label={`${metric.name} value`}
                    value={metric.value}
                    disabled={metric.mode === 'Off'}
                    onChange={(event) => updateRuleMetric(metric.name, { value: event.target.value })}
                    placeholder={metric.mode === 'Off' ? 'N/A (Off)' : 'Enter value'}
                    className={`w-full min-w-0 rounded border px-1.5 py-0.5 font-semibold outline-none transition-all ${
                      metric.mode === 'Off'
                        ? 'border-slate-200 bg-slate-100 text-slate-400 cursor-not-allowed'
                        : isBeyondLimit
                          ? 'border-red-500 bg-red-50/70 text-red-700 ring-1 ring-red-500/50 focus:border-red-600 focus:ring-red-500'
                          : 'border-slate-300 bg-white text-slate-800 placeholder:font-normal placeholder:text-slate-400 focus:border-[#238c83] focus:text-black'
                    }`}
                  />
                  {isBeyondLimit && limitSpec && (
                    <span
                      className="text-[9px] font-semibold text-red-600 mt-0.5 block truncate leading-tight"
                      title={`Limit: ${limitSpec.display}`}
                    >
                      Limit: {limitSpec.display}
                    </span>
                  )}
                </div>
                <span
                  aria-label={`${metric.name} full credit`}
                  className="text-slate-400"
                  title="Full-credit calculation is not defined by the current scoring logic."
                >
                  —
                </span>
                <div className="flex items-center gap-2">
                  {metric.mode === 'Off' || metric.mode === 'Req.' ? (
                    <div className="flex items-center justify-center w-full py-0.5 px-2 bg-slate-100 rounded text-[10px] text-slate-400 font-medium italic">
                      {metric.mode === 'Req.' ? '0% (Gate only)' : '0% (Off)'}
                    </div>
                  ) : (
                    <>
                      <input
                        aria-label={`${metric.name} weight`}
                        type="range"
                        min="0"
                        max="50"
                        value={metric.weight}
                        onChange={(event) => updateRuleMetric(metric.name, { weight: Number(event.target.value) })}
                        className="h-1.5 w-full min-w-0 cursor-pointer accent-[#238c83]"
                      />
                      <input
                        aria-label={`${metric.name} weight value`}
                        type="number"
                        min="0"
                        max="50"
                        value={metric.weight}
                        onChange={(event) =>
                          updateRuleMetric(metric.name, {
                            weight: Math.min(50, Math.max(0, Number(event.target.value) || 0)),
                          })
                        }
                        className="w-8 rounded border border-slate-300 px-1 py-0.5 text-center text-[11px] font-semibold text-slate-700 outline-none focus:border-[#238c83]"
                      />
                    </>
                  )}
                </div>
              </div>
            );
          })}
          </div>
        </section>
      </div>

      <div className={`flex items-center justify-between rounded-md border px-3 py-2 text-xs font-semibold ${
        totalWeight === 100
          ? 'border-[#238c83]/30 bg-[#eef7f6] text-slate-800'
          : 'border-[#e5a51b] bg-[#fff3cf] text-slate-800'
      }`}>
        <div className="flex items-center gap-3">
          <span>Total scoring weight: <strong>{totalWeight}%</strong></span>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
            totalWeight === 100
              ? 'bg-[#238c83] text-white'
              : 'bg-[#e5a51b]/20 text-[#9e6f0b]'
          }`}>
            {totalWeight === 100 ? 'Balanced (100%)' : `Difference: ${100 - totalWeight > 0 ? '+' : ''}${100 - totalWeight}%`}
          </span>
        </div>
        {totalWeight !== 100 && (
          <button
            onClick={autoBalanceWeights}
            className="rounded bg-[#238c83] px-2.5 py-1 text-[11px] font-bold text-white shadow-sm hover:bg-[#1b6e67] transition-colors"
          >
            Auto-Balance to 100%
          </button>
        )}
      </div>
    </div>
  );
};
