import React, { useMemo } from 'react';
import { useScreening } from '../../context/ScreeningContext';

export const MarketUniverseSelector = () => {
  const {
    countries,
    toggleCountry,
    exchanges,
    toggleExchange,
  } = useScreening();

  const selectedCountries = useMemo(
    () => countries.filter((country) => country.selected),
    [countries]
  );
  const selectedExchangeCount = useMemo(
    () => exchanges.filter((exchange) => exchange.selected).length,
    [exchanges]
  );

  return (
    <section className="rounded-md border border-slate-300 bg-white p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="mt-1 text-base font-semibold tracking-tight text-black">
            Countries &amp; exchanges
          </h2>
        </div>
        <span className="text-[11px] text-slate-500">
          {selectedCountries.length} countries · {selectedExchangeCount} exchanges selected
        </span>
      </div>
      <p className="mt-1 text-[11px] text-slate-500">
        Select where the scheduled run should fetch stock data from before configuring screening rules.
      </p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {countries.map((country) => (
          <button
            key={country.id}
            type="button"
            onClick={() => toggleCountry(country.id)}
            aria-pressed={country.selected}
            className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-colors ${
              country.selected
                ? 'border-[#238c83] bg-[#238c83] text-white'
                : 'border-slate-300 bg-white text-slate-600 hover:border-[#238c83] hover:text-[#147b73]'
            }`}
          >
            {country.name}
          </button>
        ))}
      </div>
      <div className="mt-3 border-t border-slate-200 pt-2">
        <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
          Exchanges
        </h3>
        <div className="mt-2 space-y-2">
          {selectedCountries.map((country) => {
            const countryExchanges = exchanges.filter((exchange) => exchange.countryId === country.id);
            return (
              <div key={country.id}>
                <p className="mb-1 text-[11px] font-semibold text-slate-700">{country.name}</p>
                <div className="flex flex-wrap gap-1.5">
                  {countryExchanges.map((exchange) => (
                    <button
                      key={exchange.id}
                      type="button"
                      onClick={() => toggleExchange(exchange.id)}
                      aria-pressed={exchange.selected}
                      className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                        exchange.selected
                          ? 'border-[#238c83] bg-[#238c83] text-white'
                          : 'border-slate-300 bg-white text-slate-600 hover:border-[#238c83] hover:text-[#147b73]'
                      }`}
                    >
                      {exchange.name}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
          {selectedCountries.length === 0 && (
            <p className="text-[11px] text-slate-500">
              Select a country first to choose its exchanges.
            </p>
          )}
        </div>
      </div>
      <p className="mt-3 text-[11px] text-slate-500">
        The scheduled run will request data only for the selected countries and exchanges.
      </p>
    </section>
  );
};
