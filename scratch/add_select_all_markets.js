const fs = require('fs');

// 1. Update ScreeningContext.jsx
let ctx = fs.readFileSync('frontend/src/context/ScreeningContext.jsx', 'utf8');
ctx = ctx.replace(/\r\n/g, '\n');

const targetContextCode = `  const toggleExchange = (id) => {
    setExchanges((prev) =>
      prev.map((exchange) => (exchange.id === id ? { ...exchange, selected: !exchange.selected } : exchange))
    );
  };`;

const newContextCode = `  const toggleExchange = (id) => {
    setExchanges((prev) =>
      prev.map((exchange) => (exchange.id === id ? { ...exchange, selected: !exchange.selected } : exchange))
    );
  };

  const selectAllMarkets = () => {
    const targetCountryIds = new Set(['in', 'us', 'jp', 'uk', 'de', 'ch', 'fr', 'hk', 'ca', 'kr', 'tw', 'nl', 'au', 'no', 'sg']);
    const targetExchangeIds = new Set([
      'nse', 'bse', 'nyse', 'nasdaq', 'tse', 'lse', 'xetra', 'six', 'euronext-paris',
      'hkex', 'tsx', 'krx', 'twse', 'euronext-amsterdam', 'asx', 'ose', 'sgx'
    ]);

    setCountries((prev) =>
      prev.map((c) => ({
        ...c,
        selected: targetCountryIds.has(c.id.toLowerCase()),
      }))
    );
    setExchanges((prev) =>
      prev.map((e) => ({
        ...e,
        selected: targetExchangeIds.has(e.id.toLowerCase()),
      }))
    );
  };

  const clearAllMarkets = () => {
    setCountries((prev) => prev.map((c) => ({ ...c, selected: false })));
    setExchanges((prev) => prev.map((e) => ({ ...e, selected: false })));
  };`;

if (ctx.includes(targetContextCode)) {
  ctx = ctx.replace(targetContextCode, newContextCode);
  console.log('Added selectAllMarkets and clearAllMarkets to ScreeningContext');
} else {
  console.log('WARNING: targetContextCode not found');
}

// Add to context value export
const exportTarget = `        toggleCountry,
        exchanges,
        toggleExchange,`;

const exportReplacement = `        toggleCountry,
        exchanges,
        toggleExchange,
        selectAllMarkets,
        clearAllMarkets,`;

if (ctx.includes(exportTarget)) {
  ctx = ctx.replace(exportTarget, exportReplacement);
  console.log('Exported selectAllMarkets and clearAllMarkets in ScreeningContext value');
} else {
  console.log('WARNING: exportTarget not found');
}

fs.writeFileSync('frontend/src/context/ScreeningContext.jsx', ctx, 'utf8');

// 2. Update MarketUniverseSelector.jsx
let mus = fs.readFileSync('frontend/src/components/screening-rules/MarketUniverseSelector.jsx', 'utf8');
mus = mus.replace(/\r\n/g, '\n');

const musImportTarget = `  const {
    countries,
    toggleCountry,
    exchanges,
    toggleExchange,
  } = useScreening();`;

const musImportReplacement = `  const {
    countries,
    toggleCountry,
    exchanges,
    toggleExchange,
    selectAllMarkets,
    clearAllMarkets,
  } = useScreening();`;

if (mus.includes(musImportTarget)) {
  mus = mus.replace(musImportTarget, musImportReplacement);
  console.log('Imported selectAllMarkets in MarketUniverseSelector.jsx');
} else {
  console.log('WARNING: musImportTarget not found');
}

const headerTarget = `      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="mt-1 text-base font-semibold tracking-tight text-black">
            Countries &amp; exchanges
          </h2>
        </div>
        <span className="text-[11px] text-slate-500">
          {selectedCountries.length} countries · {selectedExchangeCount} exchanges selected
        </span>
      </div>`;

const headerReplacement = `      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="mt-1 text-base font-semibold tracking-tight text-black">
            Countries &amp; exchanges
          </h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={selectAllMarkets}
            className="px-2.5 py-1 text-xs font-semibold bg-[#238c83] hover:bg-[#147b73] text-white rounded shadow-2xs transition-colors cursor-pointer flex items-center space-x-1"
            title="Select all 15 countries and 17 exchanges to screen the full 236 stocks"
          >
            <span>✓</span>
            <span>Select All Markets (All 236 Stocks)</span>
          </button>
          <button
            type="button"
            onClick={clearAllMarkets}
            className="px-2.5 py-1 text-xs font-medium bg-white hover:bg-slate-50 border border-slate-300 text-slate-600 rounded transition-colors cursor-pointer"
          >
            Clear All
          </button>
          <span className="text-[11px] text-slate-500 pl-1 font-medium">
            {selectedCountries.length} countries · {selectedExchangeCount} exchanges selected
          </span>
        </div>
      </div>`;

if (mus.includes(headerTarget)) {
  mus = mus.replace(headerTarget, headerReplacement);
  console.log('Added Select All Markets buttons in MarketUniverseSelector.jsx header');
} else {
  console.log('WARNING: headerTarget not found');
}

fs.writeFileSync('frontend/src/components/screening-rules/MarketUniverseSelector.jsx', mus, 'utf8');

