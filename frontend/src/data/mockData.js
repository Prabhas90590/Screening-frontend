// Frontend data models and default configurations.
// Mock securities have been removed so the UI will display real screening results
// fetched from the backend (mock adapter during development or real vendor in production).

export const INITIAL_SECURITIES = [];

export const INITIAL_FUNNEL = {
  universe: 0,
  markets: 0,
  floors: 0,
  gates: 0,
  score: 0,
  shortlist: 0,
  selected: 0,
  sinceLastRun: {
    entered: 0,
    exited: 0,
    notes: 'No screening runs executed yet',
  },
  runInfo: {
    runNumber: 0,
    profile: 'None',
    asOfDate: 'Awaiting screening run from backend',
  },
};

export const INITIAL_SCHEDULE = {
  profile: 'Core - v1 (current)',
  frequency: 'Weekly',
  activeDays: ['mon'],
  time: '06:00',
  timezone: 'America/New_York',
  refreshDataFirst: true,
  notifyEmail: 'pm@yourfirm.com',
  notifyTriggers: {
    runCompletes: true,
    runFails: true,
    dataBlockers: true,
  },
};

export const INITIAL_RUN_HISTORY = [];

export const INITIAL_PROFILES = [
  {
    id: 'core',
    name: 'Core',
    badge: 'Active',
    description: 'Standard long-term screen',
    betaCap: 1.0,
    leverage: 'sector table',
    weights: 'balanced',
  },
  {
    id: 'defensive',
    name: 'Defensive',
    badge: 'Saved',
    description: 'Used when equity risk is elevated',
    betaCap: 0.8,
    leverage: 'limits -0.5x',
    weights: 'quality tilt',
  },
  {
    id: 'tactical',
    name: 'Tactical',
    badge: 'Short-term',
    description: 'Theme trades; flagged not long-term',
    betaCap: 1.0,
    leverage: 'sector table',
    weights: 'momentum tilt',
    valuationRules: 'relaxed',
    maxHoldFlag: '12 months',
  },
];

export const INITIAL_VERSION_HISTORY = [
  {
    version: 'v1',
    isCurrent: true,
    date: 'Initial',
    by: 'PM',
    changeSummary: 'Baseline profile initialized',
    resultImpact: '-',
  },
];

export const INITIAL_SECTOR_LIMITS = [
  { sector: 'Utilities', limit: '', note: 'Regulated, stable cash flow' },
  { sector: 'Real Estate', limit: '', note: 'REIT convention' },
  { sector: 'Comm.', limit: '' },
  { sector: 'Energy', limit: '', note: 'Midstream may exceed' },
  { sector: 'Financials', limit: '', note: 'Excluded from test', isNa: true },
  { sector: 'Industrials', limit: '' },
  { sector: 'Materials', limit: '' },
  { sector: 'Info Tech', limit: '' },
  { sector: 'Health Care', limit: '' },
  { sector: 'Cons. Staples', limit: '' },
];

export const INITIAL_SECTORS = [
  'Energy',
  'Info Tech',
  'Real Estate',
  'Utilities',
  'Materials',
  'Health Care',
  'Industrials',
  'Financials',
  'Cons. Staples',
  'Comm.',
].map((name) => ({ name, selected: true }));

export const INITIAL_COUNTRIES = [
  { id: 'us', name: 'United States', selected: false },
  { id: 'in', name: 'India', selected: false },
  { id: 'uk', name: 'United Kingdom', selected: false },
  { id: 'jp', name: 'Japan', selected: false },
  { id: 'ca', name: 'Canada', selected: false },
  { id: 'de', name: 'Germany', selected: false },
  { id: 'fr', name: 'France', selected: false },
  { id: 'ch', name: 'Switzerland', selected: false },
  { id: 'hk', name: 'Hong Kong', selected: false },
  { id: 'sg', name: 'Singapore', selected: false },
  { id: 'au', name: 'Australia', selected: false },
  { id: 'kr', name: 'South Korea', selected: false },
  { id: 'nl', name: 'Netherlands', selected: false },
  { id: 'no', name: 'Norway', selected: false },
  { id: 'se', name: 'Sweden', selected: false },
  { id: 'cn', name: 'China', selected: false },
  { id: 'tw', name: 'Taiwan', selected: false },
  { id: 'br', name: 'Brazil', selected: false },
  { id: 'it', name: 'Italy', selected: false },
  { id: 'es', name: 'Spain', selected: false },
  { id: 'sa', name: 'Saudi Arabia', selected: false },
  { id: 'ae', name: 'United Arab Emirates', selected: false },
  { id: 'za', name: 'South Africa', selected: false },
  { id: 'id', name: 'Indonesia', selected: false },
  { id: 'mx', name: 'Mexico', selected: false },
  { id: 'nz', name: 'New Zealand', selected: false },
];

export const INITIAL_EXCHANGES = [
  // United States
  { id: 'nyse', name: 'NYSE', countryId: 'us', selected: false },
  { id: 'nasdaq', name: 'Nasdaq', countryId: 'us', selected: false },
  { id: 'cboe', name: 'Cboe BZX', countryId: 'us', selected: false },

  // India
  { id: 'nse', name: 'NSE (National Stock Exchange)', countryId: 'in', selected: false },
  { id: 'bse', name: 'BSE (Bombay Stock Exchange)', countryId: 'in', selected: false },

  // United Kingdom
  { id: 'lse', name: 'London Stock Exchange', countryId: 'uk', selected: false },

  // Japan
  { id: 'tse', name: 'Tokyo Stock Exchange', countryId: 'jp', selected: false },

  // Canada
  { id: 'tsx', name: 'Toronto Stock Exchange', countryId: 'ca', selected: false },
  { id: 'tsxv', name: 'TSX Venture Exchange', countryId: 'ca', selected: false },

  // Germany
  { id: 'xetra', name: 'Xetra', countryId: 'de', selected: false },
  { id: 'fra', name: 'Frankfurt Stock Exchange', countryId: 'de', selected: false },

  // France
  { id: 'euronext-paris', name: 'Euronext Paris', countryId: 'fr', selected: false },

  // Switzerland
  { id: 'six', name: 'SIX Swiss Exchange', countryId: 'ch', selected: false },

  // Hong Kong
  { id: 'hkex', name: 'Hong Kong Stock Exchange', countryId: 'hk', selected: false },

  // Singapore
  { id: 'sgx', name: 'Singapore Exchange', countryId: 'sg', selected: false },

  // Australia
  { id: 'asx', name: 'ASX', countryId: 'au', selected: false },

  // South Korea
  { id: 'krx', name: 'Korea Exchange (KRX)', countryId: 'kr', selected: false },

  // Netherlands
  { id: 'euronext-amsterdam', name: 'Euronext Amsterdam', countryId: 'nl', selected: false },

  // Norway
  { id: 'ose', name: 'Oslo Børs', countryId: 'no', selected: false },

  // Sweden
  { id: 'omx-stockholm', name: 'Nasdaq Stockholm', countryId: 'se', selected: false },

  // China
  { id: 'sse', name: 'Shanghai Stock Exchange', countryId: 'cn', selected: false },
  { id: 'szse', name: 'Shenzhen Stock Exchange', countryId: 'cn', selected: false },

  // Taiwan
  { id: 'twse', name: 'Taiwan Stock Exchange', countryId: 'tw', selected: false },

  // Brazil
  { id: 'b3', name: 'B3', countryId: 'br', selected: false },

  // Italy
  { id: 'milan', name: 'Borsa Italiana', countryId: 'it', selected: false },

  // Spain
  { id: 'bme-madrid', name: 'BME Spanish Exchanges', countryId: 'es', selected: false },

  // Saudi Arabia
  { id: 'tadawul', name: 'Tadawul (Saudi Exchange)', countryId: 'sa', selected: false },

  // UAE
  { id: 'dfm', name: 'Dubai Financial Market', countryId: 'ae', selected: false },
  { id: 'adx', name: 'Abu Dhabi Securities Exchange', countryId: 'ae', selected: false },

  // South Africa
  { id: 'jse', name: 'Johannesburg Stock Exchange', countryId: 'za', selected: false },

  // Indonesia
  { id: 'idx', name: 'Indonesia Stock Exchange', countryId: 'id', selected: false },

  // Mexico
  { id: 'bmv', name: 'Bolsa Mexicana de Valores', countryId: 'mx', selected: false },

  // New Zealand
  { id: 'nzx', name: 'New Zealand Exchange', countryId: 'nz', selected: false },
];

export const INITIAL_DIVERSIFICATION = {
  maxNamesPerSector: '',
  minNonUsNamesPct: '',
  maxNamesPerCountry: '',
  minSmallMidCapNames: '',
};

export const INITIAL_RULE_METRICS = [
  ['Price (USD-equiv.)', 'Size & liquidity'],
  ['Market cap (USD)', 'Size & liquidity'],
  ['Avg daily volume (shares)', 'Size & liquidity'],
  ['Avg daily traded value (USD)', 'Size & liquidity'],
  ['Data confidence', 'Quality'],
  ['Price / sales', 'Valuation'],
  ['Forward P/E vs S&P 500', 'Valuation'],
  ['PEG', 'Valuation'],
  ['EV / EBITDA', 'Valuation'],
  ['Price / cash flow', 'Valuation'],
  ['Revenue growth (5y, fwd)', 'Growth'],
  ['EPS growth (5y, fwd)', 'Growth'],
  ['Beta', 'Risk & leverage'],
  ['Net debt / EBITDA', 'Risk & leverage'],
  ['Dividend yield', 'Income'],
  ['3y / 5y return', 'Momentum'],
].map(([name, category]) => ({
  name,
  category,
  mode: 'Off',
  condition: '',
  value: '',
  weight: 0,
}));
