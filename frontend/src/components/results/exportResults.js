import * as XLSX from 'xlsx';

/**
 * Categorizes and exports screening results into a multi-tab Microsoft Excel (.xlsx) workbook.
 * 
 * Grouping structure:
 * 1. Top 20 Portfolio Selection (Ranks 1..20)
 * 2. Near Misses (Ranks 21..40 and Rule Gate Near-Misses) displayed immediately after Top 20
 * 3. Remaining Evaluated Universe
 * 
 * Also includes dedicated 'Top 20 Portfolio' and 'Near Misses' sheets for client presentations.
 */
export const exportResultsToExcel = (securities = [], profileName = '') => {
  const isTop20 = (s) =>
    (s.stageStatus === 'passed' && s.rank !== null && s.rank <= 20) ||
    (s.rank !== null && s.rank >= 1 && s.rank <= 20 && s.deltaStatus !== 'exited');

  // 1. Top 20 Portfolio (Ranks 1 to 20, sorted by rank ASC)
  const top20Securities = securities
    .filter(isTop20)
    .sort((a, b) => (a.rank || 999) - (b.rank || 999));
  const top20Ids = new Set(top20Securities.map((s) => s.id));

  // 2. Near Misses (Strictly excluding any Top 20 stocks)
  const isRankNearMiss = (s) =>
    !top20Ids.has(s.id) &&
    !isTop20(s) &&
    (s.nearMissStatus === 'rank_near_miss' || (s.rank !== null && s.rank >= 21 && s.rank <= 40));

  const isRuleNearMiss = (s) =>
    !top20Ids.has(s.id) &&
    !isTop20(s) &&
    !isRankNearMiss(s) &&
    (s.nearMissStatus === 'rule_near_miss' || s.deltaStatus === 'rule_miss' || s.rankDelta === 'RULE_MISS');

  const rankNearMisses = securities
    .filter(isRankNearMiss)
    .sort((a, b) => (a.rank || 999) - (b.rank || 999));

  const ruleNearMisses = securities
    .filter(isRuleNearMiss)
    .sort((a, b) => (b.score || 0) - (a.score || 0));

  const allNearMisses = [...rankNearMisses, ...ruleNearMisses];
  const nearMissIds = new Set(allNearMisses.map((s) => s.id));

  // 3. Remaining Universe
  const remainingUniverse = securities
    .filter((s) => !top20Ids.has(s.id) && !nearMissIds.has(s.id))
    .sort((a, b) => (b.score || 0) - (a.score || 0));

  const headers = [
    'Category',
    'Rank',
    'Security Name',
    'Ticker',
    'Exchange',
    'Sector',
    'Country',
    'Score',
    'FWD P/E',
    'PEG',
    'EV/EBITDA',
    'Beta',
    'ND/EBITDA',
    'Yield %',
    'EPS Growth %',
    'Data Confidence',
    'Status / Note',
  ];

  const formatSecurityRow = (sec, categoryLabel) => {
    const yieldDisplay =
      sec.yieldPct !== undefined && sec.yieldPct !== null && sec.yieldPct !== ''
        ? String(sec.yieldPct).includes('%')
          ? sec.yieldPct
          : `${sec.yieldPct}%`
        : '';
    const epsGrowthDisplay =
      sec.epsGrowthPct !== undefined && sec.epsGrowthPct !== null && sec.epsGrowthPct !== ''
        ? String(sec.epsGrowthPct).includes('%')
          ? sec.epsGrowthPct
          : `${sec.epsGrowthPct}%`
        : '';

    let note = sec.movementReason || '';
    if (!note) {
      if (categoryLabel.includes('Top 20')) {
        note = sec.stageStatus === 'passed' ? 'Qualified Top 20 Winner' : 'Top 20 Portfolio Selection';
      } else if (categoryLabel.includes('Rank')) {
        note = `Passed rules · Ranked #${sec.rank} (Top 20 cutoff)`;
      } else if (categoryLabel.includes('Rule')) {
        note = 'Near threshold miss on knockout gate';
      } else {
        note = 'Evaluated in universe';
      }
    }

    return [
      categoryLabel,
      sec.rank !== null && sec.rank !== undefined ? sec.rank : '',
      sec.name || '',
      sec.ticker || '',
      sec.exchange || '',
      sec.sector || '',
      sec.country || '',
      sec.score !== null && sec.score !== undefined ? sec.score : '',
      sec.fwdPe ?? '',
      sec.peg ?? '',
      sec.evEbitda ?? '',
      sec.beta ?? '',
      sec.ndEbitda ?? '',
      yieldDisplay,
      epsGrowthDisplay,
      sec.dataConfidence || 'High',
      note,
    ];
  };

  const cleanProfile = (profileName || 'equity_screener')
    .trim()
    .replace(/[^a-zA-Z0-9_-]+/g, '_')
    .replace(/^_+|_+$/g, '');
  const dateStr = new Date().toISOString().split('T')[0];
  const downloadFileName = `${cleanProfile}_${dateStr}.xlsx`;

  // Standard column widths for Excel presentation
  const colWidths = [
    { wch: 25 }, // Category
    { wch: 8 },  // Rank
    { wch: 30 }, // Security Name
    { wch: 10 }, // Ticker
    { wch: 12 }, // Exchange
    { wch: 18 }, // Sector
    { wch: 16 }, // Country
    { wch: 8 },  // Score
    { wch: 10 }, // FWD P/E
    { wch: 8 },  // PEG
    { wch: 12 }, // EV/EBITDA
    { wch: 8 },  // Beta
    { wch: 12 }, // ND/EBITDA
    { wch: 10 }, // Yield %
    { wch: 12 }, // EPS Growth %
    { wch: 16 }, // Data Confidence
    { wch: 40 }, // Status / Note
  ];

  try {
    const wb = XLSX.utils.book_new();

    // ─────────────────────────────────────────────────────────────
    // SHEET 1: Master "All Results (Categorized)"
    // Layout: Top 20 first -> Near Misses directly after -> Remaining Universe
    // ─────────────────────────────────────────────────────────────
    const masterData = [
      [`PORTFOLIO SCREENING RESULTS: ${profileName || 'ACTIVE STRATEGY'}`],
      [`Date: ${dateStr}`, `Total Screened: ${securities.length}`, `Top 20 Portfolio: ${top20Securities.length}`, `Near Misses: ${allNearMisses.length}`],
      [],
      ['=== 🏆 SECTION 1: TOP 20 PORTFOLIO SELECTION ==='],
      headers,
      ...top20Securities.map((s) => formatSecurityRow(s, 'Top 20 Portfolio')),
      [],
      ['=== ⚠️ SECTION 2: NEAR MISSES (CLOSEST CONTENDERS) ==='],
      headers,
      ...allNearMisses.map((s) =>
        formatSecurityRow(
          s,
          isRankNearMiss(s) ? 'Near Miss (Rank #21-40)' : 'Near Miss (Rule Gate)'
        )
      ),
    ];

    if (remainingUniverse.length > 0) {
      masterData.push(
        [],
        ['=== 📋 SECTION 3: OTHER EVALUATED UNIVERSE ==='],
        headers,
        ...remainingUniverse.map((s) => formatSecurityRow(s, 'Evaluated Universe'))
      );
    }

    const wsMaster = XLSX.utils.aoa_to_sheet(masterData);
    wsMaster['!cols'] = colWidths;
    XLSX.utils.book_append_sheet(wb, wsMaster, 'All Categorized');

    // ─────────────────────────────────────────────────────────────
    // SHEET 2: Dedicated "Top 20 Portfolio"
    // ─────────────────────────────────────────────────────────────
    const top20Data = [
      [`TOP 20 PORTFOLIO WINNERS - ${profileName || 'Active Strategy'}`],
      [`Export Date: ${dateStr}`, `Positions: ${top20Securities.length}`],
      [],
      headers,
      ...top20Securities.map((s) => formatSecurityRow(s, 'Top 20 Portfolio')),
    ];
    const wsTop20 = XLSX.utils.aoa_to_sheet(top20Data);
    wsTop20['!cols'] = colWidths;
    XLSX.utils.book_append_sheet(wb, wsTop20, 'Top 20 Portfolio');

    // ─────────────────────────────────────────────────────────────
    // SHEET 3: Dedicated "Near Misses"
    // ─────────────────────────────────────────────────────────────
    const nearMissData = [
      [`NEAR MISS CONTENDERS - ${profileName || 'Active Strategy'}`],
      [
        `Export Date: ${dateStr}`,
        `Total Near Misses: ${allNearMisses.length} (Rank Cutoff: ${rankNearMisses.length}, Rule Gate: ${ruleNearMisses.length})`,
      ],
      [],
      headers,
      ...allNearMisses.map((s) =>
        formatSecurityRow(
          s,
          isRankNearMiss(s) ? 'Near Miss (Rank #21-40)' : 'Near Miss (Rule Gate)'
        )
      ),
    ];
    const wsNearMiss = XLSX.utils.aoa_to_sheet(nearMissData);
    wsNearMiss['!cols'] = colWidths;
    XLSX.utils.book_append_sheet(wb, wsNearMiss, 'Near Misses');

    // ─────────────────────────────────────────────────────────────
    // SHEET 4: Executive "Summary"
    // ─────────────────────────────────────────────────────────────
    const summaryData = [
      ['Metric', 'Value'],
      ['Strategy Profile', profileName || 'Default Strategy'],
      ['Run Date', dateStr],
      ['Total Securities Evaluated', securities.length],
      ['Top 20 Portfolio Selection', top20Securities.length],
      ['Rank Near-Misses (Ranks 21-40)', rankNearMisses.length],
      ['Rule Gate Near-Misses', ruleNearMisses.length],
      ['Total Near Misses', allNearMisses.length],
      ['Remaining Evaluated Securities', remainingUniverse.length],
    ];
    const wsSummary = XLSX.utils.aoa_to_sheet(summaryData);
    wsSummary['!cols'] = [{ wch: 30 }, { wch: 30 }];
    XLSX.utils.book_append_sheet(wb, wsSummary, 'Summary');

    // Trigger Excel download
    XLSX.writeFile(wb, downloadFileName);
  } catch (err) {
    console.warn('[exportResults] XLSX.writeFile failed, falling back to structured CSV:', err);
    fallbackCsvDownload(
      top20Securities,
      allNearMisses,
      remainingUniverse,
      headers,
      formatSecurityRow,
      isRankNearMiss,
      cleanProfile,
      dateStr
    );
  }
};

/**
 * Fallback CSV export preserving the exact same structured sections & Category column
 */
const fallbackCsvDownload = (
  top20Securities,
  allNearMisses,
  remainingUniverse,
  headers,
  formatSecurityRow,
  isRankNearMiss,
  cleanProfile,
  dateStr
) => {
  const sanitizeCell = (val) => {
    const s = String(val ?? '');
    if (s.includes(',') || s.includes('"') || s.includes('\n')) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  };

  const csvRows = [
    [`### TOP 20 PORTFOLIO SELECTION ###`],
    headers.map(sanitizeCell).join(','),
    ...top20Securities.map((s) => formatSecurityRow(s, 'Top 20 Portfolio').map(sanitizeCell).join(',')),
    [],
    [`### NEAR MISSES (RANKS #21-40 & GATE MISSES) ###`],
    headers.map(sanitizeCell).join(','),
    ...allNearMisses.map((s) =>
      formatSecurityRow(
        s,
        isRankNearMiss(s) ? 'Near Miss (Rank #21-40)' : 'Near Miss (Rule Gate)'
      ).map(sanitizeCell).join(',')
    ),
  ];

  if (remainingUniverse.length > 0) {
    csvRows.push(
      [],
      [`### REMAINING EVALUATED UNIVERSE ###`],
      headers.map(sanitizeCell).join(','),
      ...remainingUniverse.map((s) => formatSecurityRow(s, 'Evaluated Universe').map(sanitizeCell).join(','))
    );
  }

  const csvContent = 'data:text/csv;charset=utf-8,\uFEFF' + csvRows.join('\n');
  const link = document.createElement('a');
  link.setAttribute('href', encodeURI(csvContent));
  link.setAttribute('download', `${cleanProfile}_${dateStr}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

// Aliases for compatibility with existing imports
export const exportResultsToCsv = exportResultsToExcel;
export default exportResultsToExcel;
