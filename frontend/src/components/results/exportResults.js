export const exportResultsToCsv = (securities = [], profileName = '') => {
  const headers = [
    'Rank',
    'Security',
    'Ticker',
    'Sector',
    'Score',
    'FWD P/E',
    'PEG',
    'EV/EBITDA',
    'Beta',
    'ND/EBITDA',
    'Yield %',
    'EPS Gr %',
    'Data Confidence',
    'Decision',
  ];
  const rows = securities.map((security) => [
    security.rank !== null && security.rank !== undefined ? security.rank : '',
    `"${(security.name || '').replace(/"/g, '""')}"`,
    security.ticker || '',
    security.sector || '',
    security.score !== null && security.score !== undefined ? security.score : '',
    security.fwdPe ?? '',
    security.peg ?? '',
    security.evEbitda ?? '',
    security.beta ?? '',
    `"${security.ndEbitda ?? ''}"`,
    security.yieldPct !== undefined && security.yieldPct !== null && security.yieldPct !== ''
      ? String(security.yieldPct).includes('%')
        ? security.yieldPct
        : `${security.yieldPct}%`
      : '',
    security.epsGrowthPct !== undefined && security.epsGrowthPct !== null && security.epsGrowthPct !== ''
      ? String(security.epsGrowthPct).includes('%')
        ? security.epsGrowthPct
        : `${security.epsGrowthPct}%`
      : '',
    security.dataConfidence || 'High',
    security.decision || 'Pending',
  ]);
  const csvContent =
    'data:text/csv;charset=utf-8,' +
    [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');

  // Format filename with clean profile name and execution date
  // e.g. "Core_v1_Version_1_2026-10-29.csv" or "Tech_Growth_v2_0_2026-10-29.csv"
  const cleanProfile = (profileName || 'equity_screener')
    .trim()
    .replace(/[^a-zA-Z0-9_-]+/g, '_')
    .replace(/^_+|_+$/g, '');
  const dateStr = new Date().toISOString().split('T')[0];
  const downloadFileName = `${cleanProfile}_${dateStr}.csv`;

  const link = document.createElement('a');
  link.setAttribute('href', encodeURI(csvContent));
  link.setAttribute('download', downloadFileName);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
