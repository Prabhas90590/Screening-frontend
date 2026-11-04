// Script to generate expanded_indian_stocks_fixtures.py containing 500 new Indian stocks
// 250 for NSE, 250 for BSE.

const fs = require('fs');
const path = require('path');

// 1. Gather all existing tickers to prevent any collision
const existingTickers = new Set();
const files = [
  path.join(__dirname, '../app/adapters/mock_adapter.py'),
  path.join(__dirname, '../app/adapters/indian_stocks_fixtures.py'),
  path.join(__dirname, '../app/adapters/global_stocks_fixtures.py'),
  path.join(__dirname, '../app/adapters/expanded_universe_fixtures.py'),
];

for (const f of files) {
  if (fs.existsSync(f)) {
    const content = fs.readFileSync(f, 'utf8');
    const regex = /"ticker":\s*"([^"]+)"/g;
    let m;
    while ((m = regex.exec(content)) !== null) {
      existingTickers.add(m[1].toUpperCase());
    }
    const codeRegex = /"Code":\s*"([^"]+)"/g;
    while ((m = codeRegex.exec(content)) !== null) {
      existingTickers.add(m[1].toUpperCase());
    }
  }
}
console.log(`Total existing tickers before Indian expansion: ${existingTickers.size}`);

// 2. Real & authentic Indian mid/small/large cap stock definitions
// Across Nifty Midcap, Smallcap, and emerging industry leaders
const INDIAN_BASE_COMPANIES = [
  // --- Mid & Large Cap IT & Digital Engineering ---
  { ticker: 'POLYCAB', name: 'Polycab India Ltd', sector: 'Industrials', baseCap: 950e9, price: 6350, fwdPe: 34.5, peg: 1.4, yieldPct: 0.6, epsGrowth: 22.5, isBank: false },
  { ticker: 'PERSISTENT', name: 'Persistent Systems Ltd', sector: 'Info Tech', baseCap: 840e9, price: 5480, fwdPe: 38.2, peg: 1.5, yieldPct: 0.7, epsGrowth: 24.0, isBank: false },
  { ticker: 'COFORGE', name: 'Coforge Ltd', sector: 'Info Tech', baseCap: 520e9, price: 7850, fwdPe: 32.1, peg: 1.35, yieldPct: 0.9, epsGrowth: 21.0, isBank: false },
  { ticker: 'TRENT', name: 'Trent Ltd', sector: 'Consumer Discretionary', baseCap: 2450e9, price: 6950, fwdPe: 68.0, peg: 1.8, yieldPct: 0.2, epsGrowth: 38.0, isBank: false },
  { ticker: 'MAXHEALTH', name: 'Max Healthcare Institute Ltd', sector: 'Health Care', baseCap: 920e9, price: 950, fwdPe: 46.5, peg: 1.6, yieldPct: 0.3, epsGrowth: 26.5, isBank: false },
  { ticker: 'DIXON', name: 'Dixon Technologies Ltd', sector: 'Industrials', baseCap: 780e9, price: 13200, fwdPe: 52.0, peg: 1.55, yieldPct: 0.2, epsGrowth: 32.0, isBank: false },
  { ticker: 'SUZLON', name: 'Suzlon Energy Ltd', sector: 'Industrials', baseCap: 880e9, price: 65, fwdPe: 36.0, peg: 1.25, yieldPct: 0.0, epsGrowth: 28.5, isBank: false },
  { ticker: 'BEL', name: 'Bharat Electronics Ltd', sector: 'Industrials', baseCap: 2150e9, price: 295, fwdPe: 35.8, peg: 1.42, yieldPct: 0.8, epsGrowth: 23.0, isBank: false },
  { ticker: 'HAL', name: 'Hindustan Aeronautics Ltd', sector: 'Industrials', baseCap: 2950e9, price: 4420, fwdPe: 34.0, peg: 1.38, yieldPct: 0.9, epsGrowth: 24.2, isBank: false },
  { ticker: 'SOLARINDS', name: 'Solar Industries India Ltd', sector: 'Materials', baseCap: 940e9, price: 10400, fwdPe: 44.5, peg: 1.5, yieldPct: 0.4, epsGrowth: 26.0, isBank: false },
  { ticker: 'ASTRAL', name: 'Astral Ltd', sector: 'Industrials', baseCap: 490e9, price: 1840, fwdPe: 42.0, peg: 1.5, yieldPct: 0.4, epsGrowth: 22.0, isBank: false },
  { ticker: 'CUMMINSIND', name: 'Cummins India Ltd', sector: 'Industrials', baseCap: 980e9, price: 3550, fwdPe: 38.5, peg: 1.45, yieldPct: 1.1, epsGrowth: 21.5, isBank: false },
  { ticker: 'LUPIN', name: 'Lupin Ltd', sector: 'Health Care', baseCap: 970e9, price: 2150, fwdPe: 27.5, peg: 1.3, yieldPct: 0.6, epsGrowth: 20.5, isBank: false },
  { ticker: 'AUROPHARMA', name: 'Aurobindo Pharma Ltd', sector: 'Health Care', baseCap: 850e9, price: 1450, fwdPe: 18.2, peg: 1.15, yieldPct: 0.5, epsGrowth: 15.5, isBank: false },
  { ticker: 'ALKEM', name: 'Alkem Laboratories Ltd', sector: 'Health Care', baseCap: 680e9, price: 5680, fwdPe: 28.0, peg: 1.3, yieldPct: 0.8, epsGrowth: 18.0, isBank: false },
  { ticker: 'TORNTPOWER', name: 'Torrent Power Ltd', sector: 'Utilities', baseCap: 820e9, price: 1710, fwdPe: 24.5, peg: 1.25, yieldPct: 1.2, epsGrowth: 19.0, isBank: false },
  { ticker: 'FEDERALBNK', name: 'The Federal Bank Ltd', sector: 'Financials', baseCap: 480e9, price: 198, fwdPe: 11.2, peg: 1.0, yieldPct: 1.1, epsGrowth: 16.5, isBank: true },
  { ticker: 'IDFCFIRSTB', name: 'IDFC First Bank Ltd', sector: 'Financials', baseCap: 520e9, price: 72, fwdPe: 14.5, peg: 1.1, yieldPct: 0.0, epsGrowth: 19.5, isBank: true },
  { ticker: 'BANDHANBNK', name: 'Bandhan Bank Ltd', sector: 'Financials', baseCap: 280e9, price: 174, fwdPe: 9.8, peg: 0.9, yieldPct: 0.9, epsGrowth: 14.0, isBank: true },
  { ticker: 'CONCOR', name: 'Container Corporation of India Ltd', sector: 'Industrials', baseCap: 540e9, price: 885, fwdPe: 28.5, peg: 1.3, yieldPct: 1.4, epsGrowth: 17.5, isBank: false },
  { ticker: 'PIIND', name: 'PI Industries Ltd', sector: 'Materials', baseCap: 680e9, price: 4450, fwdPe: 33.0, peg: 1.35, yieldPct: 0.4, epsGrowth: 21.0, isBank: false },
  { ticker: 'DEEPAKNTR', name: 'Deepak Nitrite Ltd', sector: 'Materials', baseCap: 380e9, price: 2780, fwdPe: 29.5, peg: 1.3, yieldPct: 0.4, epsGrowth: 18.5, isBank: false },
  { ticker: 'TATAELXSI', name: 'Tata Elxsi Ltd', sector: 'Info Tech', baseCap: 460e9, price: 7350, fwdPe: 41.0, peg: 1.6, yieldPct: 1.0, epsGrowth: 19.5, isBank: false },
  { ticker: 'KPITTECH', name: 'KPIT Technologies Ltd', sector: 'Info Tech', baseCap: 450e9, price: 1640, fwdPe: 45.0, peg: 1.5, yieldPct: 0.4, epsGrowth: 28.0, isBank: false },
  { ticker: 'PAGEIND', name: 'Page Industries Ltd', sector: 'Consumer Discretionary', baseCap: 490e9, price: 44200, fwdPe: 48.0, peg: 1.7, yieldPct: 0.9, epsGrowth: 16.0, isBank: false },
  { ticker: 'CHOLAFIN', name: 'Cholamandalam Investment & Finance', sector: 'Financials', baseCap: 1220e9, price: 1450, fwdPe: 23.5, peg: 1.25, yieldPct: 0.3, epsGrowth: 24.5, isBank: true },
  { ticker: 'MUTHOOTFIN', name: 'Muthoot Finance Ltd', sector: 'Financials', baseCap: 780e9, price: 1950, fwdPe: 14.8, peg: 1.15, yieldPct: 1.4, epsGrowth: 18.2, isBank: true },
  { ticker: 'SHRIRAMFIN', name: 'Shriram Finance Ltd', sector: 'Financials', baseCap: 1250e9, price: 3320, fwdPe: 12.8, peg: 1.1, yieldPct: 1.5, epsGrowth: 17.5, isBank: true },
  { ticker: 'APLAPOLLO', name: 'APL Apollo Tubes Ltd', sector: 'Industrials', baseCap: 420e9, price: 1520, fwdPe: 36.5, peg: 1.4, yieldPct: 0.4, epsGrowth: 22.0, isBank: false },
  { ticker: 'OBEROIRLTY', name: 'Oberoi Realty Ltd', sector: 'Real Estate', baseCap: 690e9, price: 1890, fwdPe: 28.0, peg: 1.3, yieldPct: 0.3, epsGrowth: 24.0, isBank: false },
  { ticker: 'PHOENIXLTD', name: 'The Phoenix Mills Ltd', sector: 'Real Estate', baseCap: 580e9, price: 1620, fwdPe: 38.0, peg: 1.4, yieldPct: 0.3, epsGrowth: 22.5, isBank: false },
  { ticker: 'PRESTIGE', name: 'Prestige Estates Projects Ltd', sector: 'Real Estate', baseCap: 640e9, price: 1590, fwdPe: 32.5, peg: 1.35, yieldPct: 0.2, epsGrowth: 25.0, isBank: false },
  { ticker: 'GODREJPROP', name: 'Godrej Properties Ltd', sector: 'Real Estate', baseCap: 810e9, price: 2920, fwdPe: 44.0, peg: 1.55, yieldPct: 0.0, epsGrowth: 26.5, isBank: false },
  { ticker: 'FORTIS', name: 'Fortis Healthcare Ltd', sector: 'Health Care', baseCap: 430e9, price: 570, fwdPe: 39.0, peg: 1.45, yieldPct: 0.3, epsGrowth: 21.0, isBank: false },
  { ticker: 'GLENMARK', name: 'Glenmark Pharmaceuticals Ltd', sector: 'Health Care', baseCap: 420e9, price: 1480, fwdPe: 19.5, peg: 1.1, yieldPct: 0.3, epsGrowth: 17.0, isBank: false },
  { ticker: 'IPCALAB', name: 'Ipca Laboratories Ltd', sector: 'Health Care', baseCap: 390e9, price: 1540, fwdPe: 31.0, peg: 1.3, yieldPct: 0.4, epsGrowth: 19.5, isBank: false },
  { ticker: 'AJANTPHARM', name: 'Ajanta Pharma Ltd', sector: 'Health Care', baseCap: 380e9, price: 3020, fwdPe: 28.5, peg: 1.25, yieldPct: 0.8, epsGrowth: 20.0, isBank: false },
  { ticker: 'JBCHEPHARM', name: 'JB Chemicals & Pharmaceuticals Ltd', sector: 'Health Care', baseCap: 290e9, price: 1880, fwdPe: 33.0, peg: 1.3, yieldPct: 0.6, epsGrowth: 22.0, isBank: false },
  { ticker: 'SYNGENE', name: 'Syngene International Ltd', sector: 'Health Care', baseCap: 340e9, price: 845, fwdPe: 42.0, peg: 1.5, yieldPct: 0.3, epsGrowth: 18.5, isBank: false },
  { ticker: 'NATCOPHARM', name: 'Natco Pharma Ltd', sector: 'Health Care', baseCap: 250e9, price: 1390, fwdPe: 16.5, peg: 1.05, yieldPct: 0.7, epsGrowth: 19.0, isBank: false },
  { ticker: 'SONACOMS', name: 'Sona BLW Precision Forgings Ltd', sector: 'Consumer Discretionary', baseCap: 420e9, price: 710, fwdPe: 48.0, peg: 1.6, yieldPct: 0.3, epsGrowth: 26.0, isBank: false },
  { ticker: 'UNOMINDA', name: 'Uno Minda Ltd', sector: 'Consumer Discretionary', baseCap: 560e9, price: 980, fwdPe: 42.5, peg: 1.5, yieldPct: 0.4, epsGrowth: 23.5, isBank: false },
  { ticker: 'BALKRISIND', name: 'Balkrishna Industries Ltd', sector: 'Consumer Discretionary', baseCap: 590e9, price: 3050, fwdPe: 29.0, peg: 1.3, yieldPct: 0.7, epsGrowth: 18.0, isBank: false },
  { ticker: 'APOLLOTYRE', name: 'Apollo Tyres Ltd', sector: 'Consumer Discretionary', baseCap: 310e9, price: 485, fwdPe: 14.5, peg: 1.1, yieldPct: 1.1, epsGrowth: 15.5, isBank: false },
  { ticker: 'MRF', name: 'MRF Ltd', sector: 'Consumer Discretionary', baseCap: 580e9, price: 137000, fwdPe: 21.0, peg: 1.25, yieldPct: 0.2, epsGrowth: 16.0, isBank: false },
  { ticker: 'BHARATFORG', name: 'Bharat Forge Ltd', sector: 'Industrials', baseCap: 680e9, price: 1460, fwdPe: 34.0, peg: 1.4, yieldPct: 0.5, epsGrowth: 21.5, isBank: false },
  { ticker: 'THERMAX', name: 'Thermax Ltd', sector: 'Industrials', baseCap: 570e9, price: 4800, fwdPe: 52.0, peg: 1.65, yieldPct: 0.3, epsGrowth: 25.0, isBank: false },
  { ticker: 'KEI', name: 'KEI Industries Ltd', sector: 'Industrials', baseCap: 410e9, price: 4550, fwdPe: 43.0, peg: 1.5, yieldPct: 0.2, epsGrowth: 24.0, isBank: false },
  { ticker: 'VOLTAS', name: 'Voltas Ltd', sector: 'Consumer Discretionary', baseCap: 580e9, price: 1750, fwdPe: 48.0, peg: 1.55, yieldPct: 0.4, epsGrowth: 25.5, isBank: false },
  { ticker: 'BLUESTARCO', name: 'Blue Star Ltd', sector: 'Consumer Discretionary', baseCap: 380e9, price: 1840, fwdPe: 46.0, peg: 1.5, yieldPct: 0.4, epsGrowth: 26.0, isBank: false },
  { ticker: 'CROMPTON', name: 'Crompton Greaves Consumer Electricals', sector: 'Consumer Discretionary', baseCap: 260e9, price: 410, fwdPe: 34.5, peg: 1.35, yieldPct: 0.8, epsGrowth: 18.5, isBank: false },
  { ticker: 'KAJARIACER', name: 'Kajaria Ceramics Ltd', sector: 'Industrials', baseCap: 210e9, price: 1320, fwdPe: 36.0, peg: 1.4, yieldPct: 0.8, epsGrowth: 17.0, isBank: false },
  { ticker: 'SUPREMEIND', name: 'Supreme Industries Ltd', sector: 'Industrials', baseCap: 610e9, price: 4800, fwdPe: 41.0, peg: 1.45, yieldPct: 0.7, epsGrowth: 20.5, isBank: false },
  { ticker: 'CENTURYPLY', name: 'Century Plyboards India Ltd', sector: 'Industrials', baseCap: 175e9, price: 790, fwdPe: 35.0, peg: 1.35, yieldPct: 0.3, epsGrowth: 19.0, isBank: false },
  { ticker: 'JUBLFOOD', name: 'Jubilant FoodWorks Ltd', sector: 'Consumer Discretionary', baseCap: 395e9, price: 600, fwdPe: 58.0, peg: 1.7, yieldPct: 0.2, epsGrowth: 23.0, isBank: false },
  { ticker: 'DEVYANI', name: 'Devyani International Ltd', sector: 'Consumer Discretionary', baseCap: 215e9, price: 178, fwdPe: 62.0, peg: 1.8, yieldPct: 0.0, epsGrowth: 27.0, isBank: false },
  { ticker: 'RADICO', name: 'Radico Khaitan Ltd', sector: 'Consumer Staples', baseCap: 295e9, price: 2210, fwdPe: 48.0, peg: 1.5, yieldPct: 0.2, epsGrowth: 24.5, isBank: false },
  { ticker: 'UNITEDSPR', name: 'United Spirits Ltd', sector: 'Consumer Staples', baseCap: 1080e9, price: 1485, fwdPe: 46.0, peg: 1.5, yieldPct: 0.4, epsGrowth: 22.0, isBank: false },
  { ticker: 'MANKIND', name: 'Mankind Pharma Ltd', sector: 'Health Care', baseCap: 1050e9, price: 2620, fwdPe: 41.5, peg: 1.45, yieldPct: 0.3, epsGrowth: 21.5, isBank: false },
  { ticker: 'AARTIIND', name: 'Aarti Industries Ltd', sector: 'Materials', baseCap: 195e9, price: 540, fwdPe: 27.0, peg: 1.25, yieldPct: 0.4, epsGrowth: 16.5, isBank: false },
  { ticker: 'VINATIORGA', name: 'Vinati Organics Ltd', sector: 'Materials', baseCap: 198e9, price: 1920, fwdPe: 38.0, peg: 1.4, yieldPct: 0.4, epsGrowth: 21.0, isBank: false },
  { ticker: 'NAVINFLUOR', name: 'Navin Fluorine International Ltd', sector: 'Materials', baseCap: 170e9, price: 3420, fwdPe: 44.0, peg: 1.5, yieldPct: 0.3, epsGrowth: 23.0, isBank: false },
  { ticker: 'ATUL', name: 'Atul Ltd', sector: 'Materials', baseCap: 225e9, price: 7650, fwdPe: 36.0, peg: 1.35, yieldPct: 0.4, epsGrowth: 18.5, isBank: false },
  { ticker: 'GUJGASLTD', name: 'Gujarat Gas Ltd', sector: 'Utilities', baseCap: 380e9, price: 550, fwdPe: 26.0, peg: 1.2, yieldPct: 1.0, epsGrowth: 17.0, isBank: false },
  { ticker: 'IGL', name: 'Indraprastha Gas Ltd', sector: 'Utilities', baseCap: 285e9, price: 408, fwdPe: 16.0, peg: 1.1, yieldPct: 2.2, epsGrowth: 12.5, isBank: false },
  { ticker: 'MGL', name: 'Mahanagar Gas Ltd', sector: 'Utilities', baseCap: 175e9, price: 1770, fwdPe: 13.5, peg: 1.05, yieldPct: 2.3, epsGrowth: 13.5, isBank: false },
  { ticker: 'PETRONET', name: 'Petronet LNG Ltd', sector: 'Energy', baseCap: 520e9, price: 348, fwdPe: 12.0, peg: 1.0, yieldPct: 2.9, epsGrowth: 12.0, isBank: false },
  { ticker: 'COROMANDEL', name: 'Coromandel International Ltd', sector: 'Materials', baseCap: 480e9, price: 1630, fwdPe: 21.0, peg: 1.2, yieldPct: 0.9, epsGrowth: 15.5, isBank: false },
  { ticker: 'UPL', name: 'UPL Ltd', sector: 'Materials', baseCap: 410e9, price: 545, fwdPe: 15.0, peg: 1.1, yieldPct: 1.8, epsGrowth: 11.0, isBank: false },
  { ticker: 'JSL', name: 'Jindal Stainless Ltd', sector: 'Materials', baseCap: 610e9, price: 740, fwdPe: 18.5, peg: 1.15, yieldPct: 0.5, epsGrowth: 17.5, isBank: false },
  { ticker: 'SAIL', name: 'Steel Authority of India Ltd', sector: 'Materials', baseCap: 530e9, price: 128, fwdPe: 14.0, peg: 1.1, yieldPct: 1.6, epsGrowth: 13.0, isBank: false },
  { ticker: 'NMDC', name: 'NMDC Ltd', sector: 'Materials', baseCap: 660e9, price: 225, fwdPe: 10.5, peg: 0.95, yieldPct: 3.2, epsGrowth: 14.5, isBank: false },
  { ticker: 'HINDCOPPER', name: 'Hindustan Copper Ltd', sector: 'Materials', baseCap: 295e9, price: 305, fwdPe: 34.0, peg: 1.35, yieldPct: 0.3, epsGrowth: 21.0, isBank: false },
  { ticker: 'NATIONALUM', name: 'National Aluminium Co Ltd', sector: 'Materials', baseCap: 410e9, price: 224, fwdPe: 12.5, peg: 1.05, yieldPct: 2.5, epsGrowth: 15.0, isBank: false },
  { ticker: 'JKCEMENT', name: 'JK Cement Ltd', sector: 'Materials', baseCap: 345e9, price: 4450, fwdPe: 31.0, peg: 1.3, yieldPct: 0.4, epsGrowth: 19.5, isBank: false },
  { ticker: 'DALBHARAT', name: 'Dalmia Bharat Ltd', sector: 'Materials', baseCap: 350e9, price: 1860, fwdPe: 32.0, peg: 1.35, yieldPct: 0.3, epsGrowth: 18.0, isBank: false },
  { ticker: 'RAMCOCEM', name: 'The Ramco Cements Ltd', sector: 'Materials', baseCap: 215e9, price: 910, fwdPe: 34.0, peg: 1.35, yieldPct: 0.4, epsGrowth: 16.5, isBank: false },
  { ticker: 'APOLLOHOSP2', name: 'Apollo Hospitals Enterprise', sector: 'Health Care', baseCap: 1040e9, price: 7240, fwdPe: 48.0, peg: 1.55, yieldPct: 0.3, epsGrowth: 24.5, isBank: false },
  { ticker: 'CYIENT', name: 'Cyient Ltd', sector: 'Info Tech', baseCap: 210e9, price: 1890, fwdPe: 23.0, peg: 1.25, yieldPct: 1.5, epsGrowth: 17.0, isBank: false },
  { ticker: 'ZENSARTECH', name: 'Zensar Technologies Ltd', sector: 'Info Tech', baseCap: 175e9, price: 765, fwdPe: 22.0, peg: 1.2, yieldPct: 1.6, epsGrowth: 16.5, isBank: false },
  { ticker: 'BSOFT', name: 'Birlasoft Ltd', sector: 'Info Tech', baseCap: 185e9, price: 670, fwdPe: 24.0, peg: 1.25, yieldPct: 1.2, epsGrowth: 18.0, isBank: false },
  { ticker: 'MASTEK', name: 'Mastek Ltd', sector: 'Info Tech', baseCap: 88e9, price: 2880, fwdPe: 21.0, peg: 1.2, yieldPct: 0.8, epsGrowth: 16.0, isBank: false },
  { ticker: 'SONATSOFTW', name: 'Sonata Software Ltd', sector: 'Info Tech', baseCap: 165e9, price: 590, fwdPe: 27.0, peg: 1.3, yieldPct: 1.4, epsGrowth: 19.5, isBank: false },
  { ticker: 'LATENTVIEW', name: 'Latent View Analytics Ltd', sector: 'Info Tech', baseCap: 105e9, price: 510, fwdPe: 46.0, peg: 1.55, yieldPct: 0.0, epsGrowth: 22.0, isBank: false },
  { ticker: 'HAPPSTMNDS', name: 'Happiest Minds Technologies', sector: 'Info Tech', baseCap: 125e9, price: 820, fwdPe: 42.0, peg: 1.5, yieldPct: 0.5, epsGrowth: 20.5, isBank: false },
  { ticker: 'NEWGEN', name: 'Newgen Software Technologies', sector: 'Info Tech', baseCap: 155e9, price: 1110, fwdPe: 38.0, peg: 1.4, yieldPct: 0.4, epsGrowth: 25.0, isBank: false },
  { ticker: 'INTELLECT', name: 'Intellect Design Arena Ltd', sector: 'Info Tech', baseCap: 135e9, price: 985, fwdPe: 34.0, peg: 1.35, yieldPct: 0.4, epsGrowth: 21.0, isBank: false },
  { ticker: 'RATEGAIN', name: 'RateGain Travel Technologies', sector: 'Info Tech', baseCap: 92e9, price: 780, fwdPe: 44.0, peg: 1.5, yieldPct: 0.0, epsGrowth: 26.0, isBank: false },
  { ticker: 'MAPMYINDIA', name: 'C.E. Info Systems Ltd', sector: 'Info Tech', baseCap: 118e9, price: 2180, fwdPe: 55.0, peg: 1.65, yieldPct: 0.2, epsGrowth: 28.0, isBank: false },
  { ticker: 'AFFLE', name: 'Affle (India) Ltd', sector: 'Info Tech', baseCap: 215e9, price: 1540, fwdPe: 48.0, peg: 1.55, yieldPct: 0.0, epsGrowth: 25.5, isBank: false },
  { ticker: 'ECLERX', name: 'eClerx Services Ltd', sector: 'Info Tech', baseCap: 145e9, price: 2980, fwdPe: 22.5, peg: 1.25, yieldPct: 0.3, epsGrowth: 17.5, isBank: false },
  { ticker: 'DATAPATTNS', name: 'Data Patterns (India) Ltd', sector: 'Industrials', baseCap: 145e9, price: 2620, fwdPe: 52.0, peg: 1.6, yieldPct: 0.2, epsGrowth: 29.0, isBank: false },
  { ticker: 'MTARTECH', name: 'MTAR Technologies Ltd', sector: 'Industrials', baseCap: 52e9, price: 1690, fwdPe: 44.0, peg: 1.5, yieldPct: 0.0, epsGrowth: 22.0, isBank: false },
  { ticker: 'ASTRAMICRO', name: 'Astra Microwave Products Ltd', sector: 'Industrials', baseCap: 84e9, price: 885, fwdPe: 36.0, peg: 1.35, yieldPct: 0.2, epsGrowth: 24.5, isBank: false },
  { ticker: 'ZEN', name: 'Zen Technologies Ltd', sector: 'Industrials', baseCap: 155e9, price: 1840, fwdPe: 65.0, peg: 1.75, yieldPct: 0.1, epsGrowth: 35.0, isBank: false },
];

console.log(`Curated base company templates: ${INDIAN_BASE_COMPANIES.length}`);

// Pools for generating rich authentic Indian names when scaling to 500
const INDIAN_NAME_PREFIXES = [
  'Adani', 'Reliance', 'Tata', 'Birla', 'Mahindra', 'Bajaj', 'Godrej', 'Larsen', 'Jindal', 'Hero',
  'TVS', 'Kalyan', 'Sundaram', 'Murugappa', 'GMR', 'GVK', 'Jaypee', 'Essar', 'Vedanta', 'Ambuja',
  'Shree', 'Orient', 'Century', 'Prism', 'JK', 'Somany', 'Supreme', 'Finolex', 'Prince', 'Astral',
  'Havells', 'Crompton', 'Voltas', 'BlueStar', 'Symphony', 'Whirlpool', 'V-Guard', 'Polycab', 'KEI', 'FinCables',
  'KEC', 'Kalpataru', 'Sterling', 'Praj', 'Thermax', 'BHEL', 'BEL', 'HAL', 'Mazagon', 'GardenReach',
  'Cochin', 'BharatForge', 'AIA', 'Cummins', 'Action', 'Escorts', 'Force', 'SML', 'Olectra', 'JBM',
  'Motherson', 'UnoMinda', 'SonaBLW', 'Varroc', 'Endurance', 'Suprajit', 'Lumax', 'Fiem', 'Pricol', 'Subros',
  'Apollo', 'MRF', 'CEAT', 'JKTyre', 'Balkrishna', 'TVS-Srichakra', 'Goodyear', 'Bridgestone', 'Gabriel', 'Banco',
  'SunPharma', 'DrReddy', 'Cipla', 'Lupin', 'Aurobindo', 'Zydus', 'Torrent', 'Alkem', 'Glenmark', 'Biocon',
  'Mankind', 'Ipca', 'Ajanta', 'JBChem', 'Natco', 'Granules', 'Eris', 'Alembic', 'Neuland', 'Marksans',
  'HDFC', 'ICICI', 'Axis', 'Kotak', 'SBI', 'BankOfBaroda', 'Canara', 'PunjabNational', 'UnionBank', 'IndianBank',
  'FederalBank', 'IDFCFirst', 'Bandhan', 'IndusInd', 'RBL', 'CityUnion', 'KarurVysya', 'AU-SmallFinance', 'Equitas', 'Ujjivan',
  'BajajFinance', 'ShriramFinance', 'Cholamandalam', 'Muthoot', 'Manappuram', 'Poonawalla', 'L&T-Finance', 'SundaramFin', 'MahindraFin', 'TataCap',
  'HDFCLife', 'SBILife', 'ICICIPrudential', 'MaxFinancial', 'LIC-India', 'StarHealth', 'ICICILombard', 'GeneralInsurance', 'NewIndia', 'GIC-Re',
  'ITC', 'HindustanUnilever', 'Nestle', 'Britannia', 'Dabur', 'Marico', 'GodrejConsumer', 'Colgate', 'Emami', 'Jyothy',
  'VarunBeverages', 'UnitedSpirits', 'Radico', 'UnitedBreweries', 'Sula', 'Bikaji', 'Prataap', 'DFM', 'TastyBite', 'MrsBectors',
  'Titan', 'KalyanJewellers', 'Senco', 'Thangamayil', 'PC-Jeweller', 'Trent', 'DMart', 'ShoppersStop', 'V-Mart', 'AdityaFashion',
  'PageInd', 'Bata', 'Relaxo', 'Campus', 'Redtape', 'MetroBrands', 'KPR-Mill', 'Gokaldas', 'Arvind', 'Raymond',
  'DLF', 'Macrotech', 'GodrejProperties', 'OberoiRealty', 'Prestige', 'Sobha', 'Brigade', 'SignatureGlobal', 'Puravankara', 'KoltePatil',
  'NTPC', 'PowerGrid', 'TataPower', 'AdaniPower', 'AdaniGreen', 'JSW-Energy', 'TorrentPower', 'NHPC', 'SJVN', 'CESC',
  'ONGC', 'OilIndia', 'IndianOil', 'BPCL', 'HPCL', 'Petronet', 'GAIL', 'GujaratGas', 'IGL', 'MGL',
];

const INDIAN_SUFFIXES = [
  'Industries Ltd', 'Enterprises Ltd', 'Technologies Ltd', 'Solutions Ltd', 'Holdings Ltd',
  'Infrastructure Ltd', 'Engineering Ltd', 'Power Ltd', 'Chemicals Ltd', 'Pharma Ltd',
  'Finance Ltd', 'Capital Ltd', 'Consumer Ltd', 'Ventures Ltd', 'International Ltd',
  'Corporation Ltd', 'Services Ltd', 'Systems Ltd', 'Logistics Ltd', 'Developers Ltd'
];

const SECTORS = [
  'Info Tech', 'Financials', 'Health Care', 'Consumer Discretionary', 'Consumer Staples',
  'Industrials', 'Energy', 'Materials', 'Utilities', 'Communication Services', 'Real Estate'
];

const records = [];
let idxCounter = 0;

function getNextUniqueTicker(seedName, exchange, num) {
  let clean = seedName.replace(/[^A-Za-z0-9]/g, '').toUpperCase();
  if (clean.length > 8) clean = clean.substring(0, 8);
  
  let cand = clean;
  let attempt = 0;
  while (existingTickers.has(cand)) {
    attempt++;
    cand = `${clean.substring(0, Math.min(6, clean.length))}${attempt}`;
    if (cand.length > 10) {
      cand = `IN${exchange.toUpperCase()}${num}`;
    }
  }
  existingTickers.add(cand);
  return cand;
}

// 3. Generate exactly 250 for NSE and 250 for BSE (Total: 500)
const EXCHANGES_CONFIG = [
  { exchange: 'nse', target: 250 },
  { exchange: 'bse', target: 250 },
];

for (const cfg of EXCHANGES_CONFIG) {
  for (let i = 0; i < cfg.target; i++) {
    idxCounter++;
    const isTemplate = i < INDIAN_BASE_COMPANIES.length;
    let comp = isTemplate ? INDIAN_BASE_COMPANIES[i] : null;

    let ticker, name, sector, isBank, baseCap, price, fwdPe, peg, yieldPct, epsGrowth;

    if (comp) {
      ticker = getNextUniqueTicker(comp.ticker, cfg.exchange, idxCounter);
      name = `${comp.name} (${cfg.exchange.toUpperCase()})`;
      sector = comp.sector;
      isBank = comp.isBank;
      baseCap = comp.baseCap * (0.95 + ((idxCounter % 15) / 100));
      price = comp.price * (0.98 + ((idxCounter % 8) / 100));
      fwdPe = comp.fwdPe;
      peg = comp.peg;
      yieldPct = comp.yieldPct;
      epsGrowth = comp.epsGrowth;
    } else {
      const pIdx = (idxCounter * 17) % INDIAN_NAME_PREFIXES.length;
      const sIdx = (idxCounter * 11) % INDIAN_SUFFIXES.length;
      const prefix = INDIAN_NAME_PREFIXES[pIdx];
      const suffix = INDIAN_SUFFIXES[sIdx];
      name = `${prefix} ${suffix}`;
      
      sector = SECTORS[(idxCounter * 13) % SECTORS.length];
      isBank = sector === 'Financials' && (idxCounter % 3 === 0);
      ticker = getNextUniqueTicker(prefix, cfg.exchange, idxCounter);

      // Midcap / Smallcap INR ranges (₹3,500 Cr to ₹85,000 Cr)
      baseCap = Math.round((35e9 + ((idxCounter * 123457) % 850) * 1e8));
      price = Math.round((85.0 + ((idxCounter * 43) % 4500)) * 100) / 100;
      fwdPe = Math.round((12.5 + ((idxCounter * 19) % 350) / 10.0) * 10) / 10;
      peg = Math.round((0.8 + ((idxCounter * 7) % 14) / 10.0) * 100) / 100;
      yieldPct = Math.round(((idxCounter * 5) % 35) / 10.0 * 10) / 10;
      epsGrowth = Math.round((10.0 + ((idxCounter * 11) % 250) / 10.0) * 10) / 10;
    }

    let ebitda = Math.round(baseCap * (0.09 + ((idxCounter % 14) / 100)));
    let netDebt = Math.round(ebitda * (0.7 + ((idxCounter % 28) / 10.0)));
    let beta = Math.round((0.65 + ((idxCounter * 17) % 85) / 100.0) * 100) / 100;
    let revenue = Math.round(ebitda * (2.8 + ((idxCounter % 20) / 10.0)));
    let volume = Math.round(350000 + ((idxCounter * 9431) % 18000000));
    let asOfDate = '2026-11-03';

    // Institutional edge cases
    if (isBank) {
      ebitda = null;
      netDebt = null;
      peg = 1.15;
      yieldPct = Math.max(0.5, yieldPct);
    } else if (sector === 'Health Care' && (idxCounter % 8 === 0)) {
      // Biotech turnaround: negative EBITDA
      fwdPe = null;
      peg = null;
      ebitda = -Math.round(250e6 * 84.1);
      netDebt = -Math.round(800e6 * 84.1);
      epsGrowth = -12.5;
      yieldPct = 0.0;
    } else if (sector === 'Info Tech' && (idxCounter % 4 === 0)) {
      // Cash rich debt-free IT firm
      netDebt = -Math.round(baseCap * 0.12);
    } else if (idxCounter % 75 === 0) {
      // High debt / capital intensive infra
      netDebt = Math.round(ebitda * 4.8);
    }

    const isinCode = `INE${String(idxCounter).padStart(3, '0')}${ticker.padEnd(5, '0').substring(0, 5)}${idxCounter % 10}`;

    records.push({
      ticker,
      name,
      country: 'IN',
      exchange: cfg.exchange,
      sector,
      currency: 'INR',
      isin: isinCode,
      market_cap: Math.round(baseCap),
      close_price: price,
      fwdPe,
      peg,
      ebitda,
      net_debt: netDebt,
      beta,
      yieldPct,
      epsGrowthPct: epsGrowth,
      revenue,
      avg_daily_volume: volume,
      as_of_date: asOfDate,
      is_bank: isBank ? true : undefined,
    });
  }
}

console.log(`Generated exactly ${records.length} new Indian stocks.`);

// 4. Format into Python file
const pyHeader = `"""Expanded Indian stock fixtures (500 securities across NSE and BSE).

Adds comprehensive coverage of Indian mid-cap, small-cap, and sector leaders:
- 250 equities listed on NSE (National Stock Exchange)
- 250 equities listed on BSE (Bombay Stock Exchange)

Includes institutional edge cases:
1. Banking and NBFC leverage exemptions (ebitda: None, net_debt: None, is_bank: True)
2. Cash-rich Net Cash balance sheets (net_debt < 0)
3. Infrastructure and capital-intensive leverage stress tests (Net Debt / EBITDA > 4.5x)
4. Turnaround and negative-EBITDA biotech/chemical edge cases
5. High-growth mid-cap momentum profiles
"""

from typing import Any, Dict, List

EXPANDED_INDIAN_MOCK_SECURITIES: List[Dict[str, Any]] = [
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

const outputPath = path.join(__dirname, '../app/adapters/expanded_indian_stocks_fixtures.py');
fs.writeFileSync(outputPath, pyHeader + pyItems + pyFooter, 'utf8');
console.log(`Successfully written 500 Indian fixtures to ${outputPath}`);

