import React, { useMemo } from 'react';
import { useScreening } from '../../context/ScreeningContext';

export const LimitsUniverseDiversification = () => {
  const {
    sectorLimits,
    updateSectorLimit,
    updateSectorNote,
    sectors,
    toggleSector,
    setAllSectors,
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
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold tracking-tight text-black">
              Sector universe
            </h2>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setAllSectors?.(true)}
                className="rounded border border-slate-300 bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Select All
              </button>
              <button
                type="button"
                onClick={() => setAllSectors?.(false)}
                className="rounded border border-slate-300 bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Clear All
              </button>
            </div>
          </div>
          <p className="mb-2 text-[11px] text-slate-500">
            Select the sectors to include in this screening run ({selectedSectorNames.length} of {sectors.length} selected).
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
            <span className="text-[11px] font-medium text-slate-500">
              Limit: 0.0x – 15.0x · condition: &lt;=
            </span>
          </div>
          <p className="mb-2 text-[11px] text-slate-500">
            Enter a value only when this sector needs a different maximum. Leave blank to use general Rule Catalog limit
            {generalLimit ? ` of ${generalLimit}x` : '.'}
          </p>
          <div className="grid grid-cols-[minmax(110px,1fr)_94px_minmax(120px,1.25fr)] border-b border-slate-200 px-2 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
            <span>Sector</span>
            <span className="text-center">Max &lt;= (0.0x–15.0x)</span>
            <span>Note</span>
          </div>
          <div className="divide-y divide-slate-100">
            {visibleSectorLimits.length === 0 ? (
              <p className="py-4 text-center text-xs text-slate-500 italic">
                No sectors currently selected. Select sectors above to configure overrides.
              </p>
            ) : (
              visibleSectorLimits.map((item) => {
                const numLimit = item.limit !== '' && !isNaN(Number(item.limit)) ? Number(item.limit) : null;
                const isDebtBeyondLimit = numLimit !== null && (numLimit < 0.0 || numLimit > 15.0);

                return (
                  <div
                    key={item.sector}
                    className="grid grid-cols-[minmax(110px,1fr)_94px_minmax(120px,1.25fr)] items-center gap-2 px-2 py-1.5 text-xs"
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
                    <div className="flex flex-col items-center">
                      <input
                        aria-label={`${item.sector} debt to EBITDA limit`}
                        type="number"
                        min="0"
                        max="15"
                        step="0.1"
                        value={item.limit}
                        onChange={(event) => updateSectorLimit(item.sector, event.target.value)}
                        placeholder="—"
                        className={`w-full rounded-md border px-2 py-1 text-center text-xs outline-none transition-all ${
                          isDebtBeyondLimit
                            ? 'border-red-500 bg-red-50/70 text-red-700 ring-1 ring-red-500/50 focus:border-red-600 focus:ring-red-500'
                            : 'border-slate-300 bg-white text-slate-700 focus:border-[#238c83] focus:ring-1 focus:ring-[#238c83]/20'
                        }`}
                      />
                      {isDebtBeyondLimit && (
                        <span className="text-[9px] font-semibold text-red-600 mt-0.5 block text-center leading-tight">
                          Limit: 0.0x–15.0x
                        </span>
                      )}
                    </div>
                    <input
                      aria-label={`${item.sector} note`}
                      value={item.note || ''}
                      onChange={(event) => updateSectorNote(item.sector, event.target.value)}
                      placeholder="Optional note"
                      className="w-full min-w-0 rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px] text-slate-600 outline-none focus:border-[#238c83] focus:ring-1 focus:ring-[#238c83]/20"
                    />
                  </div>
                );
              })
            )}
          </div>
        </section>

        <div className="space-y-3">
          <section className="rounded-md border border-slate-300 bg-white p-2.5">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold tracking-tight text-black">
                Diversification constraints (final top 20)
              </h2>
              <span className="text-[10px] font-semibold text-[#147b73] bg-[#e1f0ed] px-2 py-0.5 rounded-full">
                Portfolio: Top 20 stocks
              </span>
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              Institutional exposure limits applied across the final top 20 shortlisted securities.
            </p>
            <div className="mt-2 divide-y divide-slate-100">
              <ConstraintInput
                label="Max names per sector"
                value={diversification.maxNamesPerSector}
                onChange={(value) => updateDiversification({ maxNamesPerSector: value })}
                limitLabel="1 – 20 stocks"
                minLimit={1}
                maxLimit={20}
                step="1"
              />
              <ConstraintInput
                label="Min non-US names"
                value={diversification.minNonUsNamesPct}
                onChange={(value) => updateDiversification({ minNonUsNamesPct: value })}
                suffix="%"
                limitLabel="0% – 100%"
                minLimit={0}
                maxLimit={100}
                step="1"
              />
              <ConstraintInput
                label="Max names per country (non-US)"
                value={diversification.maxNamesPerCountry}
                onChange={(value) => updateDiversification({ maxNamesPerCountry: value })}
                limitLabel="1 – 20 stocks"
                minLimit={1}
                maxLimit={20}
                step="1"
              />
              <ConstraintInput
                label="Min small / mid-cap names"
                value={diversification.minSmallMidCapNames}
                onChange={(value) => updateDiversification({ minSmallMidCapNames: value })}
                limitLabel="0 – 20 stocks"
                minLimit={0}
                maxLimit={20}
                step="1"
              />
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

const ConstraintInput = ({
  label,
  value,
  suffix,
  onChange,
  limitLabel,
  minLimit,
  maxLimit,
  ...inputProps
}) => {
  const numValue = value === '' || value === undefined ? null : Number(value);
  const isExceeded =
    numValue !== null &&
    !isNaN(numValue) &&
    ((minLimit !== undefined && numValue < minLimit) ||
      (maxLimit !== undefined && numValue > maxLimit));

  return (
    <div className="py-2.5">
      <div className="flex items-center justify-between gap-4 text-xs">
        <div>
          <span className="font-medium text-slate-700">{label}</span>
          {limitLabel && (
            <span className="ml-2 text-[10px] font-normal text-slate-400">
              (Limit: {limitLabel})
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <input
            {...inputProps}
            type="number"
            value={value}
            onChange={(event) => {
              const nextValue = event.target.value;
              onChange(nextValue === '' ? '' : Number(nextValue));
            }}
            placeholder="—"
            className={`w-16 rounded-md border px-2 py-1 text-right text-xs font-semibold outline-none transition-all ${
              isExceeded
                ? 'border-red-500 bg-red-50/70 text-red-700 ring-1 ring-red-500/50 focus:border-red-600 focus:ring-red-500'
                : 'border-slate-300 bg-white text-slate-700 focus:border-[#238c83] focus:ring-1 focus:ring-[#238c83]/20'
            }`}
          />
          {suffix && <span className="text-xs font-medium text-slate-500">{suffix}</span>}
        </div>
      </div>
      {isExceeded && (
        <div className="mt-1 flex justify-end">
          <span className="text-[10px] font-semibold text-red-600 bg-red-50 border border-red-200 rounded px-1.5 py-0.5">
            Must be {limitLabel} (Top 20 portfolio)
          </span>
        </div>
      )}
    </div>
  );
};
