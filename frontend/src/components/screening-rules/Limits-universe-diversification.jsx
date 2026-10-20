import React, { useMemo } from 'react';
import { useScreening } from '../../context/ScreeningContext';

export const LimitsUniverseDiversification = () => {
  const {
    sectorLimits,
    updateSectorLimit,
    updateSectorNote,
    sectors,
    toggleSector,
    ruleMetrics,
    diversification,
    updateDiversification,
  } = useScreening();

  const selectedSectorNames = useMemo(
    () => sectors.filter((sector) => sector.selected).map((sector) => sector.name),
    [sectors]
  );
  const visibleSectorLimits = sectorLimits.filter((item) => selectedSectorNames.includes(item.sector));
  const netDebtMetric = ruleMetrics.find((metric) => metric.name === 'Net debt / EBITDA');
  const generalLimit = netDebtMetric?.value?.trim();

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1.03fr_0.97fr]">
      <section className="rounded-md border border-slate-300 bg-white p-2.5">
        <h2 className="mb-2 text-sm font-semibold tracking-tight text-black">
          Sector universe
        </h2>
        <p className="mb-2 text-[11px] text-slate-500">
          Select the sectors to include in this screening run. This does not automatically create a sector-specific debt rule.
        </p>
        <div className="mb-3 flex flex-wrap gap-1.5">
          {sectors.map((sector) => (
            <button
              key={sector.name}
              type="button"
              onClick={() => toggleSector(sector.name)}
              aria-pressed={sector.selected}
              className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                sector.selected
                  ? 'border-[#238c83] bg-[#238c83] text-white'
                  : 'border-slate-300 bg-white text-slate-600 hover:border-[#238c83] hover:text-[#147b73]'
              }`}
            >
              {sector.name}
            </button>
          ))}
        </div>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold tracking-tight text-black">
            Max net debt / EBITDA by sector
          </h3>
          <span className="text-[11px] text-slate-500">Optional override · condition: &lt;=</span>
        </div>
        <p className="mb-2 text-[11px] text-slate-500">
          Enter a value only when this sector needs a different maximum. Leave it blank to use the general Rule Catalog limit
          {generalLimit ? ` of ${generalLimit}x` : '.'}
        </p>
        <div className="grid grid-cols-[minmax(120px,1fr)_84px_minmax(120px,1.25fr)] border-b border-slate-200 px-2 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          <span>Sector</span>
          <span>Max &lt;=</span>
          <span>Note</span>
        </div>
        <div className="divide-y divide-slate-100">
          {visibleSectorLimits.map((item) => (
            <div
              key={item.sector}
              className="grid grid-cols-[minmax(120px,1fr)_84px_minmax(120px,1.25fr)] items-center gap-2 px-2 py-1.5 text-xs"
            >
              <div>
                <span className="font-semibold text-slate-800">{item.sector}</span>
                <p className="text-[10px] text-slate-500">
                  {item.limit !== ''
                    ? `Effective limit: ${item.limit}x (sector override)`
                    : generalLimit
                      ? `Effective limit: ${generalLimit}x (general rule)`
                      : 'Effective limit: general rule not set'}
                </p>
              </div>
              <input
                aria-label={`${item.sector} debt to EBITDA limit`}
                type="number"
                min="0"
                step="0.1"
                value={item.limit}
                onChange={(event) => updateSectorLimit(item.sector, event.target.value)}
                placeholder="Enter limit"
                className="w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-center text-xs text-slate-700 outline-none focus:border-[#238c83] focus:ring-1 focus:ring-[#238c83]/20"
              />
              <input
                aria-label={`${item.sector} note`}
                value={item.note}
                onChange={(event) => updateSectorNote(item.sector, event.target.value)}
                placeholder="Enter note"
                className="w-full min-w-0 rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px] text-slate-600 outline-none focus:border-[#238c83] focus:ring-1 focus:ring-[#238c83]/20"
              />
            </div>
          ))}
        </div>
      </section>

      <div className="space-y-3">
        <section className="rounded-md border border-slate-300 bg-white p-2.5">
          <h2 className="text-sm font-semibold tracking-tight text-black">
            Diversification constraints (final top 20)
          </h2>
          <div className="mt-2 divide-y divide-slate-100">
            <ConstraintInput
              label="Max names per sector"
              value={diversification.maxNamesPerSector}
              onChange={(value) => updateDiversification({ maxNamesPerSector: value })}
              min="0"
              step="1"
            />
            <ConstraintInput
              label="Min non-US names"
              value={diversification.minNonUsNamesPct}
              suffix="%"
              onChange={(value) => updateDiversification({ minNonUsNamesPct: value })}
              min="0"
              max="100"
              step="1"
            />
            <ConstraintInput
              label="Max names per country (non-US)"
              value={diversification.maxNamesPerCountry}
              onChange={(value) => updateDiversification({ maxNamesPerCountry: value })}
              min="0"
              step="1"
            />
            <ConstraintInput
              label="Min small / mid-cap names"
              value={diversification.minSmallMidCapNames}
              onChange={(value) => updateDiversification({ minSmallMidCapNames: value })}
              min="0"
              step="1"
            />
          </div>
        </section>
      </div>
    </div>
    </div>
  );
};

const ConstraintInput = ({ label, value, suffix, onChange, ...inputProps }) => (
  <label className="flex items-center justify-between gap-4 py-2 text-xs">
    <span className="font-medium text-slate-700">{label}</span>
    <span className="flex items-center gap-1">
      <input
        {...inputProps}
        type="number"
        value={value}
        onChange={(event) => {
          const nextValue = event.target.value;
          onChange(nextValue === '' ? '' : Number(nextValue));
        }}
        className="w-14 rounded-md border border-slate-300 bg-white px-2 py-1 text-right text-xs text-slate-700 outline-none focus:border-[#238c83] focus:ring-1 focus:ring-[#238c83]/20"
      />
      {suffix && <span className="text-slate-500">{suffix}</span>}
    </span>
  </label>
);