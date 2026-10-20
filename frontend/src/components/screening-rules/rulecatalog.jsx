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

export const RuleCatalog = () => {
  const {
    ruleMetrics,
    updateRuleMetric,
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
          <div className="grid grid-cols-[minmax(145px,1.5fr)_176px_76px_minmax(72px,0.7fr)_70px_minmax(150px,1fr)] items-center gap-2 border-b border-slate-200 px-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
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
            ) : visibleMetrics.map((metric) => (
              <div
                key={metric.name}
                className="grid grid-cols-[minmax(145px,1.5fr)_176px_76px_minmax(72px,0.7fr)_70px_minmax(150px,1fr)] items-center gap-2 border-b border-slate-100 px-2 py-1 text-[11px] last:border-b-0"
              >
                <span className={`font-semibold ${metric.mode === 'Off' ? 'text-slate-400' : 'text-slate-800'}`}>
                  {metric.name}
                </span>
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
                <input
                  aria-label={`${metric.name} value`}
                  value={metric.value}
                  onChange={(event) => updateRuleMetric(metric.name, { value: event.target.value })}
                  placeholder="Enter value"
                  className="w-full min-w-0 rounded border border-slate-300 bg-white px-1 py-0.5 font-semibold text-slate-800 outline-none placeholder:font-normal placeholder:text-slate-400 focus:border-[#238c83] focus:text-black"
                />
                <span
                  aria-label={`${metric.name} full credit`}
                  className="text-slate-400"
                  title="Full-credit calculation is not defined by the current scoring logic."
                >
                  —
                </span>
                <div className="flex items-center gap-2">
                  <input
                    aria-label={`${metric.name} weight`}
                    type="range"
                    min="0"
                    max="20"
                    value={metric.weight}
                    onChange={(event) => updateRuleMetric(metric.name, { weight: Number(event.target.value) })}
                    className="h-1.5 w-full min-w-0 cursor-pointer accent-[#238c83]"
                  />
                  <input
                    aria-label={`${metric.name} weight value`}
                    type="number"
                    min="0"
                    max="20"
                    value={metric.weight}
                    onChange={(event) =>
                      updateRuleMetric(metric.name, {
                        weight: Math.min(20, Math.max(0, Number(event.target.value) || 0)),
                      })
                    }
                    className="w-8 rounded border border-slate-300 px-1 py-0.5 text-center text-[11px] text-slate-700 outline-none focus:border-[#238c83]"
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="flex items-center gap-3 rounded-md border border-[#e5a51b] bg-[#fff3cf] px-3 py-2 text-xs font-semibold text-slate-800">
        <span>Total weight {totalWeight}</span>
        <span className="rounded-full bg-[#d3eee9] px-2 py-1 text-[10px] font-bold text-[#147b73]">
          {totalWeight === 100 ? 'balanced' : 'adjust weights to 100'}
        </span>
      </div>
    </div>
  );
};
