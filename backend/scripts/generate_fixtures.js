// Script to generate expanded_universe_fixtures.py containing 764 high-quality mock stocks
// Combined with existing 236 stocks (16 RAW + 100 INDIAN + 120 GLOBAL), total = 1,000 stocks.

const fs = require('fs');
const path = require('path');

// 1. Read existing tickers to guarantee zero collisions
const indianText = fs.readFileSync(path.join(__dirname, '../app/adapters/indian_stocks_fixtures.py'), 'utf8');
const globalText = fs.readFileSync(path.join(__dirname, '../app/adapters/global_stocks_fixtures.py'), 'utf8');
const mockText = fs.readFileSync(path.join(__dirname, '../app/adapters/mock_adapter.py'), 'utf8');

const existingTickers = new Set();
const regex = /"ticker":\s*"([^"]+)"/g;
let m;
for (const txt of [indianText, globalText, mockText]) {
  while ((m = regex.exec(txt)) !== null) {
    existingTickers.add(m[1].toUpperCase());
  }
}
console.log(`Found ${existingTickers.size} existing tickers across current fixtures.`);

// 2. Exchange & Country specifications (Sum = 764)
const EXCHANGE_SPECS = [
  // United States (194 stocks total)
  { exchange: 'nasdaq', country: 'US', currency: 'USD', count: 87, fx: 1.0 },
  { exchange: 'nyse', country: 'US', currency: 'USD', count: 87, fx: 1.0 },
  { exchange: 'cboe', country: 'US', currency: 'USD', count: 20, fx: 1.0 },

  // India (50 stocks total)
  { exchange: 'nse', country: 'IN', currency: 'INR', count: 25, fx: 84.1 },
  { exchange: 'bse', country: 'IN', currency: 'INR', count: 25, fx: 84.1 },

  // United Kingdom (39 stocks)
  { exchange: 'lse', country: 'UK', currency: 'GBP', count: 39, fx: 0.79 },

  // Japan (45 stocks)
  { exchange: 'tse', country: 'JP', currency: 'JPY', count: 45, fx: 152.5 },

  // Canada (35 stocks)
  { exchange: 'tsx', country: 'CA', currency: 'CAD', count: 25, fx: 1.38 },
  { exchange: 'tsxv', country: 'CA', currency: 'CAD', count: 10, fx: 1.38 },

  // Germany (35 stocks)
  { exchange: 'xetra', country: 'DE', currency: 'EUR', count: 25, fx: 0.92 },
  { exchange: 'fra', country: 'DE', currency: 'EUR', count: 10, fx: 0.92 },

  // France (30 stocks)
  { exchange: 'euronext-paris', country: 'FR', currency: 'EUR', count: 30, fx: 0.92 },

  // Switzerland (22 stocks)
  { exchange: 'six', country: 'CH', currency: 'CHF', count: 22, fx: 0.87 },

  // Hong Kong (25 stocks)
  { exchange: 'hkex', country: 'HK', currency: 'HKD', count: 25, fx: 7.77 },

  // Singapore (18 stocks)
  { exchange: 'sgx', country: 'SG', currency: 'SGD', count: 18, fx: 1.32 },

  // Australia (25 stocks)
  { exchange: 'asx', country: 'AU', currency: 'AUD', count: 25, fx: 1.51 },

  // South Korea (25 stocks)
  { exchange: 'krx', country: 'KR', currency: 'KRW', count: 25, fx: 1380.0 },

  // Netherlands (18 stocks)
  { exchange: 'euronext-amsterdam', country: 'NL', currency: 'EUR', count: 18, fx: 0.92 },

  // Norway (15 stocks)
  { exchange: 'ose', country: 'NO', currency: 'NOK', count: 15, fx: 10.95 },

  // Sweden (18 stocks)
  { exchange: 'omx-stockholm', country: 'SE', currency: 'SEK', count: 18, fx: 10.55 },

  // China (30 stocks)
  { exchange: 'sse', country: 'CN', currency: 'CNY', count: 16, fx: 7.12 },
  { exchange: 'szse', country: 'CN', currency: 'CNY', count: 14, fx: 7.12 },

  // Taiwan (18 stocks)
  { exchange: 'twse', country: 'TW', currency: 'TWD', count: 18, fx: 32.1 },

  // Brazil (16 stocks)
  { exchange: 'b3', country: 'BR', currency: 'BRL', count: 16, fx: 5.7 },

  // Italy (16 stocks)
  { exchange: 'milan', country: 'IT', currency: 'EUR', count: 16, fx: 0.92 },

  // Spain (16 stocks)
  { exchange: 'bme-madrid', country: 'ES', currency: 'EUR', count: 16, fx: 0.92 },

  // Saudi Arabia (12 stocks)
  { exchange: 'tadawul', country: 'SA', currency: 'SAR', count: 12, fx: 3.75 },

  // UAE (16 stocks)
  { exchange: 'dfm', country: 'AE', currency: 'AED', count: 8, fx: 3.67 },
  { exchange: 'adx', country: 'AE', currency: 'AED', count: 8, fx: 3.67 },

  // South Africa (12 stocks)
  { exchange: 'jse', country: 'ZA', currency: 'ZAR', count: 12, fx: 17.8 },

  // Indonesia (12 stocks)
  { exchange: 'idx', country: 'ID', currency: 'IDR', count: 12, fx: 15600.0 },

  // Mexico (12 stocks)
  { exchange: 'bmv', country: 'MX', currency: 'MXN', count: 12, fx: 19.85 },

  // New Zealand (10 stocks)
  { exchange: 'nzx', country: 'NZ', currency: 'NZD', count: 10, fx: 1.67 },
];

const SECTORS = [
  'Info Tech',
  'Financials',
  'Health Care',
  'Consumer Discretionary',
  'Consumer Staples',
  'Industrials',
  'Energy',
  'Materials',
  'Utilities',
  'Communication Services',
  'Real Estate',
];

// Curated naming pools for authentic international companies
const COMPANY_NAME_PREFIXES = {
  US: ['Apex', 'Vanguard', 'Pinnacle', 'Summit', 'Nexus', 'Horizon', 'Beacon', 'Quantum', 'Aero', 'Starlight', 'Pacific', 'Atlantic', 'Matrix', 'Global', 'Vertex', 'Synergy', 'Orion', 'Titan', 'Cascade', 'Centennial', 'Zenith', 'Keystone', 'Omni', 'Pioneer', 'Frontier'],
  IN: ['Shree', 'Aditya', 'Mahindra', 'Godrej', 'Kotak', 'Bajaj', 'Larsen', 'Wipro', 'HCL', 'Vedanta', 'Cipla', 'Sun', 'DrReddy', 'Apollo', 'UltraTech', 'Grasim', 'Hindalco', 'JSW', 'Tata', 'Reliance', 'Maruti', 'Havells', 'Britannia', 'Dabur', 'Marico'],
  UK: ['Barclays', 'Prudential', 'Legal & General', 'Rolls-Royce', 'BAE', 'Compass', 'Reckitt', 'Smith & Nephew', 'Bunzl', 'Severn Trent', 'Halma', 'Spirax', 'Rentokil', 'Intertek', 'Sage', 'Croda', 'Mondi', 'Burberry', 'Pearson', 'Whitbread'],
  JP: ['Mitsubishi', 'Mitsui', 'Sumitomo', 'Nomura', 'Panasonic', 'Hitachi', 'Daiichi', 'Takeda', 'Shiseido', 'Daikin', 'Denso', 'Komatsu', 'Kubota', 'Olympus', 'Fujitsu', 'Canon', 'Kyocera', 'Omron', 'SMC', 'Nidec'],
  CA: ['Brookfield', 'Enbridge', 'TC Energy', 'Canadian National', 'Nutrien', 'Manulife', 'Sun Life', 'Constellation', 'Alimentation', 'CGI', 'BCE', 'Telus', 'Pembina', 'Fortis', 'Metro', 'Toromont', 'OpenText', 'Stantec', 'WSP', 'GFL'],
  DE: ['Siemens Energy', 'Bayer AG', 'Continental', 'Infineon', 'Munich Re', 'Henkel', 'Fresenius', 'Beiersdorf', 'Symrise', 'Brenntag', 'Qiagen', 'Zalando', 'Heidelberg', 'Covestro', 'Puma', 'GEA Group', 'Nemetschek', 'Knorr-Bremse', 'Delivery Hero', 'Aixtron'],
  FR: ['Sanofi', 'Schneider', 'Air Liquide', 'Hermes', 'Kering', 'Vinci', 'Danone', 'Saint-Gobain', 'Capgemini', 'Dassault', 'Pernod Ricard', 'Legrand', 'Engie', 'Carrefour', 'Michelin', 'Publicis', 'Thales', 'Veolia', 'Edenred', 'Alstom'],
  CH: ['Roche', 'Novartis Pharma', 'ABB Ltd', 'Sika AG', 'Givaudan', 'Alcon', 'Lonza Group', 'Holcim', 'Sonova', 'Kuehne+Nagel', 'Swisscom', 'Straumann', 'Partners Group', 'Geberit', 'Lindt & Sprüngli', 'Schindler', 'Swatch', 'Temenos', 'Adecco', 'Baloise'],
  HK: ['CK Hutchison', 'Sun Hung Kai', 'Hong Kong Exchanges', 'CLP Holdings', 'AIA Group', 'Hang Seng', 'Galaxy Entertainment', 'Link REIT', 'Henderson Land', 'New World', 'Wharf Real Estate', 'Sino Land', 'MTR Corporation', 'ESR Group', 'Techtronic'],
  SG: ['Singtel', 'DBS Group', 'Oversea-Chinese Banking', 'United Overseas Bank', 'Wilmar International', 'Singapore Airlines', 'CapitaLand', 'Keppel Corp', 'Sembcorp', 'City Developments', 'Singapore Exchange', 'ComfortDelGro', 'Seatrium', 'Venture Corp', 'SATS'],
  AU: ['BHP Group', 'Commonwealth Bank', 'CSL Ltd', 'National Australia Bank', 'Westpac', 'ANZ Group', 'Macquarie', 'Woodside Energy', 'Wesfarmers', 'Telstra', 'Rio Tinto Aus', 'Woolworths', 'Transurban', 'Fortescue', 'Goodman Group'],
  KR: ['Samsung Electronics', 'SK Hynix', 'Hyundai Motor', 'Samsung Biologics', 'LG Chem', 'Kia Corp', 'Celltrion', 'POSCO Holdings', 'Naver Corp', 'Kakao', 'Samsung SDI', 'LG Electronics', 'Hyundai Mobis', 'Shinhan Financial', 'KB Financial'],
  NL: ['ASML Holding', 'Prosus', 'ING Group', 'Adyen', 'Ahold Delhaize', 'Wolters Kluwer', 'Heineken NV', 'DSM-Firmenich', 'Akzo Nobel', 'KPN', 'NN Group', 'Arcadis', 'Signify', 'ASM International', 'BE Semiconductor'],
  NO: ['Equinor', 'DNB Bank', 'Telenor', 'Yara International', 'Norsk Hydro', 'Mowi', 'Orkla', 'Storebrand', 'Gjensidige', 'Tomra Systems', 'SalMar', 'Kongsberg Gruppen', 'Aker BP', 'Bakkafrost', 'Schibsted'],
  SE: ['Investor AB', 'Atlas Copco', 'Volvo AB', 'Assa Abloy', 'Sandvik', 'Hexagon', 'Skandinaviska Enskilda', 'Swedbank', 'Handelsbanken', 'Ericsson', 'Essity', 'Evolution', 'Alfa Laval', 'Boliden', 'Nibe Industrier'],
  CN: ['Kweichow Moutai', 'Contemporary Amperex', 'BYD Company', 'Ping An Insurance', 'China Merchants Bank', 'Wuliangye Yibin', 'China Yangtze Power', 'Midea Group', 'PetroChina', 'Sinopec', 'Industrial & Commercial Bank', 'Agricultural Bank', 'China Shenhua', 'Fosun Pharma', 'Hikvision'],
  TW: ['Taiwan Semiconductor', 'MediaTek', 'Hon Hai Precision', 'Delta Electronics', 'United Microelectronics', 'Chunghwa Telecom', 'Fubon Financial', 'Cathay Financial', 'Mega Financial', 'ASE Technology', 'Formosa Plastics', 'Nan Ya Plastics', 'Uni-President', 'China Steel', 'Largan Precision'],
  BR: ['Petrobras', 'Vale SA', 'Itaú Unibanco', 'Banco Bradesco', 'Ambev SA', 'WEG SA', 'Banco do Brasil', 'Itaúsa', 'Suzano', 'B3 SA', 'Rede D\'Or', 'Eletrobras', 'Gerdau', 'JBS SA', 'Cosan', 'Raízen'],
  IT: ['Ferrari NV', 'Enel SpA', 'Intesa Sanpaolo', 'Eni SpA', 'UniCredit', 'STMicroelectronics', 'Moncler', 'Prysmian', 'Assicurazioni Generali', 'Terna', 'Snam', 'Recordati', 'Poste Italiane', 'Mediobanca', 'Nexi', 'FinecoBank'],
  ES: ['Iberdrola', 'Banco Santander', 'Inditex', 'BBVA', 'Amadeus IT', 'Cellnex Telecom', 'Ferrovial', 'CaixaBank', 'Telefonica', 'Repsol', 'Aena SME', 'ACS Group', 'Acciona', 'Grifols', 'Redeia', 'Endesa'],
  SA: ['Saudi Aramco', 'Al Rajhi Bank', 'Saudi National Bank', 'SABIC', 'Saudi Telecom', 'Ma\'aden', 'Riyad Bank', 'Alinma Bank', 'Banque Saudi Fransi', 'SABIC Agri-Nutrients', 'Dr Sulaiman Al Habib', 'Etihad Etisalat'],
  AE: ['Emirates NBD', 'First Abu Dhabi Bank', 'Emaar Properties', 'Abu Dhabi Commercial Bank', 'Dubai Islamic Bank', 'Etisalat e&', 'ADNOC Gas', 'Aldar Properties', 'Dubai Electricity & Water', 'Americana', 'Salik Company', 'Air Arabia'],
  ZA: ['Naspers', 'FirstRand', 'Standard Bank', 'Gold Fields', 'Capitec Bank', 'AngloGold Ashanti', 'Sasol', 'MTN Group', 'Vodacom', 'Sanlam', 'Shoprite Holdings', 'Bidvest Group'],
  ID: ['Bank Central Asia', 'Bank Rakyat Indonesia', 'Bank Mandiri', 'Telkom Indonesia', 'Astra International', 'Chandra Asri', 'Bank Negara Indonesia', 'Indofood', 'Unilever Indonesia', 'Kalbe Farma', 'Adaro Energy', 'United Tractors'],
  MX: ['América Móvil', 'Wal-Mart de México', 'Fomento Económico Mexicano', 'Grupo México', 'Grupo Financiero Banorte', 'Cemex', 'Grupo Bimbo', 'Arca Continental', 'Fibra Uno', 'Gruma', 'Liverpool', 'Orbia Advance'],
  NZ: ['Fisher & Paykel Healthcare', 'Auckland International Airport', 'Meridian Energy', 'Contact Energy', 'Spark New Zealand', 'Infratil', 'Mainfreight', 'Ebos Group', 'Mercury NZ', 'Fletcher Building'],
};

const SUFFIXES = ['Corp', 'Holdings', 'Group', 'Industries', 'Systems', 'Technologies', 'Energy', 'Capital', 'Global', 'Solutions', 'Partners', 'International'];

let generatedCount = 0;
const generatedTickers = new Set();
const records = [];

function generateUniqueTicker(country, exchange, idx) {
  const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  let cand = '';
  let tries = 0;
  while (tries < 1000) {
    if (exchange === 'tse') {
      // Japan: 4-digit numeric ticker
      cand = `${4000 + (idx % 5900)}`;
    } else if (exchange === 'hkex') {
      // HK: 4-digit code e.g. 0981
      cand = String(800 + idx).padStart(4, '0');
    } else if (exchange === 'krx') {
      // KR: 6-digit code e.g. 035420
      cand = String(30000 + (idx * 17)).padStart(6, '0');
    } else if (exchange === 'twse') {
      // TW: 4-digit code e.g. 2454
      cand = `${2300 + idx}`;
    } else if (exchange === 'sse' || exchange === 'szse') {
      // China: 6-digit code
      const prefix = exchange === 'sse' ? '60' : '00';
      cand = `${prefix}${String(1000 + idx).padStart(4, '0')}`;
    } else {
      // Standard alphabetical ticker 3-5 letters
      const c1 = letters[(idx * 7) % 26];
      const c2 = letters[(idx * 13 + 3) % 26];
      const c3 = letters[(idx * 19 + 7) % 26];
      const c4 = (idx % 2 === 0) ? letters[(idx * 5 + 11) % 26] : '';
      cand = `${c1}${c2}${c3}${c4}`;
    }

    if (!existingTickers.has(cand) && !generatedTickers.has(cand)) {
      generatedTickers.add(cand);
      return cand;
    }
    tries++;
    idx += 79;
  }
  cand = `T${generatedCount}${country.substring(0, 2)}`;
  generatedTickers.add(cand);
  return cand;
}

// Generate the 764 records
let globalIdx = 0;

for (const spec of EXCHANGE_SPECS) {
  const namePool = COMPANY_NAME_PREFIXES[spec.country] || ['Global', 'Pacific', 'Continental', 'International'];
  
  for (let i = 0; i < spec.count; i++) {
    globalIdx++;
    generatedCount++;

    const ticker = generateUniqueTicker(spec.country, spec.exchange, globalIdx);
    const prefix = namePool[i % namePool.length];
    const suffix = SUFFIXES[(globalIdx + i) % SUFFIXES.length];
    const name = `${prefix} ${suffix}`;
    const sector = SECTORS[(globalIdx + i) % SECTORS.length];
    
    // Scale market cap in local currency using FX rate
    // Base USD Cap between $800M and $180B
    const baseCapUSD = 8e8 + ((globalIdx * 1234567891) % 180) * 1e9;
    const marketCap = Math.round(baseCapUSD * spec.fx);

    // Realistic share price in local currency
    const basePriceUSD = 15.0 + ((globalIdx * 37) % 450);
    let closePrice = Math.round(basePriceUSD * spec.fx * 100) / 100;

    // Realistic Financials
    const isBank = sector === 'Financials' && (i % 2 === 0);
    const isBiotechLossMaker = sector === 'Health Care' && (i % 4 === 1);
    const isCashRichTech = sector === 'Info Tech' && (i % 3 === 0);
    const isValueTrap = (globalIdx % 50 === 0); // 1 in 50 outlier
    const isMinorCurrencyLSE = (spec.exchange === 'lse' && i === 0); // GBp test

    let fwdPe = 8.5 + ((globalIdx * 17) % 280) / 10.0;
    let peg = 0.6 + ((globalIdx * 11) % 20) / 10.0;
    let ebitda = Math.round(marketCap * (0.08 + ((globalIdx % 15) / 100.0)));
    let netDebt = Math.round(ebitda * (0.8 + ((globalIdx % 30) / 10.0)));
    let beta = Math.round((0.45 + ((globalIdx * 23) % 135) / 100.0) * 100) / 100;
    let yieldPct = Math.round((0.5 + ((globalIdx * 19) % 65) / 10.0) * 10) / 10;
    let epsGrowthPct = Math.round((-4.0 + ((globalIdx * 29) % 380) / 10.0) * 10) / 10;
    let revenue = Math.round(ebitda * (2.5 + ((globalIdx % 20) / 10.0)));
    let volume = Math.round(500000 + ((globalIdx * 8831) % 25000000));
    let asOfDate = '2026-11-03';
    let currency = spec.currency;

    // Apply Real-World Institutional Edge Cases
    if (isBank) {
      ebitda = null;
      netDebt = null;
      peg = 1.1;
      yieldPct = 4.2;
    } else if (isBiotechLossMaker) {
      fwdPe = null;
      peg = null;
      ebitda = -Math.round(45e6 * spec.fx); // Negative EBITDA
      netDebt = -Math.round(120e6 * spec.fx);
      epsGrowthPct = -14.5;
      yieldPct = 0.0;
    } else if (isCashRichTech) {
      netDebt = -Math.round(marketCap * 0.15); // Large Net Cash
      fwdPe = 22.4;
      peg = 1.2;
      epsGrowthPct = 16.5;
    } else if (isValueTrap) {
      yieldPct = 38.5; // Distressed high dividend yield outlier
      fwdPe = 1200.0;  // Hyper-distorted P/E outlier
    } else if (isMinorCurrencyLSE) {
      currency = 'GBp'; // Minor Pence currency
      closePrice = Math.round(closePrice * 100);
    }

    // Staleness edge test: 3 stocks slightly lagged
    if (globalIdx === 42 || globalIdx === 142 || globalIdx === 342) {
      asOfDate = '2026-10-31';
    }

    const isinCode = `${spec.country}${ticker.padEnd(9, '0').substring(0, 9)}${globalIdx % 10}`;

    records.push({
      ticker,
      name,
      country: spec.country,
      exchange: spec.exchange,
      sector,
      currency,
      isin: isinCode,
      market_cap: marketCap,
      close_price: closePrice,
      fwdPe,
      peg,
      ebitda,
      net_debt: netDebt,
      beta,
      yieldPct,
      epsGrowthPct,
      revenue,
      avg_daily_volume: volume,
      as_of_date: asOfDate,
      is_bank: isBank ? true : undefined,
    });
  }
}

console.log(`Generated exactly ${records.length} mock records.`);

// Format output as clean Python code
const pyHeader = `"""Expanded universe mock fixture data (764 securities across 26 countries & 34 exchanges).

Combined with:
- RAW_MOCK_SECURITIES (16)
- INDIAN_MOCK_SECURITIES (100)
- GLOBAL_MOCK_SECURITIES (120)

Total mock universe = 1,000 equities.

Includes comprehensive institutional edge cases:
1. Banking & Finance Net Debt / EBITDA exemptions
2. Negative EBITDA & speculative biotech loss-makers
3. Net Cash balance sheets (negative Net Debt)
4. Minor currency units (UK GBp pence)
5. Outliers and extreme value traps (P/E > 1,000x, Dividend Yield > 30%)
6. Full multi-currency coverage (USD, EUR, GBP, JPY, CAD, CHF, AUD, INR, KRW, HKD, SGD, BRL, CNY, TWD, SAR, AED, ZAR, IDR, MXN, NZD, SEK, NOK)
"""

from typing import Any, Dict, List

EXPANDED_MOCK_SECURITIES: List[Dict[str, Any]] = [
`;

const pyItems = records.map((r) => {
  const lines = ['    {'];
  lines.push(`        "ticker": "${r.ticker}",`);
  lines.push(`        "name": "${r.name.replace(/"/g, '\\"')}",`);
  lines.push(`        "country": "${r.country}",`);
  lines.push(`        "exchange": "${r.exchange}",`);
  lines.push(`        "sector": "${r.sector}",`);
  lines.push(`        "currency": "${r.currency}",`);
  lines.push(`        "isin": "${r.isin}",`);
  lines.push(`        "market_cap": ${r.market_cap},`);
  lines.push(`        "close_price": ${r.close_price},`);
  lines.push(`        "fwdPe": ${r.fwdPe === null ? 'None' : r.fwdPe},`);
  lines.push(`        "peg": ${r.peg === null ? 'None' : r.peg},`);
  lines.push(`        "ebitda": ${r.ebitda === null ? 'None' : r.ebitda},`);
  lines.push(`        "net_debt": ${r.net_debt === null ? 'None' : r.net_debt},`);
  lines.push(`        "beta": ${r.beta},`);
  lines.push(`        "yieldPct": ${r.yieldPct},`);
  lines.push(`        "epsGrowthPct": ${r.epsGrowthPct},`);
  lines.push(`        "revenue": ${r.revenue},`);
  lines.push(`        "avg_daily_volume": ${r.avg_daily_volume},`);
  lines.push(`        "as_of_date": "${r.as_of_date}",`);
  if (r.is_bank) {
    lines.push(`        "is_bank": True,`);
  }
  lines.push('    },');
  return lines.join('\n');
}).join('\n');

const pyFooter = `
]
`;

const outputPath = path.join(__dirname, '../app/adapters/expanded_universe_fixtures.py');
fs.writeFileSync(outputPath, pyHeader + pyItems + pyFooter, 'utf8');
console.log(`Successfully wrote ${records.length} fixtures to ${outputPath}`);
