export const exportResultsToCsv = (securities) => {
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
    security.rank,
    `"${security.name}"`,
    security.ticker,
    security.sector,
    security.score,
    security.fwdPe,
    security.peg,
    security.evEbitda,
    security.beta,
    `"${security.ndEbitda}"`,
    `${security.yieldPct}%`,
    `${security.epsGrowthPct}%`,
    security.dataConfidence,
    security.decision || 'Pending',
  ]);
  const csvContent =
    'data:text/csv;charset=utf-8,' +
    [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
  const link = document.createElement('a');
  link.setAttribute('href', encodeURI(csvContent));
  link.setAttribute(
    'download',
    `equity_screener_${new Date().toISOString().split('T')[0]}.csv`
  );
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
