import { useState, useEffect, useCallback } from 'react';
import * as XLSX from 'xlsx';
import { fetchHoldings, uploadHoldingsFile as apiUploadHoldings, clearHoldings as apiClearHoldings } from '../../services/api';

export const useHoldingsImport = (securities = []) => {
  const [persistentHoldings, setPersistentHoldings] = useState([]);
  const [holdingIds, setHoldingIds] = useState([]);
  const [holdingsUploadError, setHoldingsUploadError] = useState('');
  const [holdingsUploadSummary, setHoldingsUploadSummary] = useState('');
  const [uploadedHoldingRows, setUploadedHoldingRows] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Load persistent holdings from PostgreSQL on initial mount
  const loadPersistentHoldings = useCallback(async () => {
    try {
      const serverHoldings = await fetchHoldings();
      if (serverHoldings && Array.isArray(serverHoldings)) {
        setPersistentHoldings(serverHoldings);
        if (serverHoldings.length > 0) {
          const ids = serverHoldings.map((h) => h.canonical_company_id || h.holding_id);
          setHoldingIds(ids);
          setHoldingsUploadSummary(`Active portfolio loaded (${serverHoldings.length} positions stored).`);
        } else {
          setHoldingIds([]);
          setHoldingsUploadSummary('');
        }
      }
    } catch (err) {
      console.warn('[useHoldingsImport] Could not load holdings from backend:', err);
    }
  }, []);

  // Clear holdings from database and UI state
  const clearPortfolioHoldings = async () => {
    setIsLoading(true);
    setHoldingsUploadError('');
    try {
      await apiClearHoldings();
      setPersistentHoldings([]);
      setHoldingIds([]);
      setUploadedHoldingRows([]);
      setHoldingsUploadSummary('Portfolio cleared. Ready for new holdings upload.');
    } catch (err) {
      console.warn('[useHoldingsImport] Could not clear holdings from backend:', err);
      setPersistentHoldings([]);
      setHoldingIds([]);
      setUploadedHoldingRows([]);
      setHoldingsUploadSummary('Portfolio cleared.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPersistentHoldings();
  }, [loadPersistentHoldings]);

  const uploadHoldingsFile = async (file) => {
    if (!file) return;

    setHoldingsUploadError('');
    setHoldingsUploadSummary('Uploading and reconciling with Security Master...');
    setIsLoading(true);

    try {
      // 1. Send file to Phase 15 backend API for PostgreSQL storage & Security Master reconciliation
      const result = await apiUploadHoldings(file);

      if (result && result.holdings) {
        setPersistentHoldings(result.holdings);
        const ids = result.holdings.map((h) => h.canonical_company_id || h.holding_id);
        setHoldingIds(ids);
        setHoldingsUploadSummary(result.message || `${result.matched_count} holdings loaded into portfolio.`);
        setIsLoading(false);
        return;
      }
    } catch (apiErr) {
      console.warn('[useHoldingsImport] Backend upload failed, falling back to local XLSX parsing:', apiErr);
    }

    // 2. Client-side fallback if backend is offline
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const workbook = XLSX.read(event.target?.result, { type: 'array' });
        if (!workbook.SheetNames || !workbook.SheetNames.length) {
          setHoldingsUploadError('The selected spreadsheet contains no worksheets.');
          setIsLoading(false);
          return;
        }

        // Search for best sheet: prefer sheets named top 20, holdings, portfolio, positions, universe
        let targetSheet = workbook.Sheets[workbook.SheetNames[0]];
        for (const sName of workbook.SheetNames) {
          const sLower = sName.toLowerCase();
          if (
            sLower.includes('holding') ||
            sLower.includes('portfolio') ||
            sLower.includes('top 20') ||
            sLower.includes('top20') ||
            sLower.includes('positions') ||
            sLower.includes('universe')
          ) {
            targetSheet = workbook.Sheets[sName];
            break;
          }
        }

        const rawAoa = XLSX.utils.sheet_to_json(targetSheet, { header: 1, defval: '' });
        if (!rawAoa || !rawAoa.length) {
          setHoldingsUploadError('The selected spreadsheet does not contain any data rows.');
          setUploadedHoldingRows([]);
          setHoldingIds([]);
          setIsLoading(false);
          return;
        }

        // Dynamically find header row across title banners (scan first 40 rows)
        const TICKER_HEADER_CANDIDATES = [
          'ticker',
          'symbol',
          'securitysymbol',
          'stocksymbol',
          'stock',
          'securityid',
          'code',
          'isin',
          'identifier',
          'asset',
          'security',
        ];
        let headerRowIdx = -1;
        for (let r = 0; r < Math.min(rawAoa.length, 40); r++) {
          const row = rawAoa[r];
          if (
            Array.isArray(row) &&
            row.some((cell) => {
              const norm = String(cell || '').trim().toLowerCase().replace(/[^a-z0-9]/g, '');
              return TICKER_HEADER_CANDIDATES.includes(norm);
            })
          ) {
            headerRowIdx = r;
            break;
          }
        }

        if (headerRowIdx === -1) {
          for (let r = 0; r < rawAoa.length; r++) {
            if (Array.isArray(rawAoa[r]) && rawAoa[r].some((c) => String(c).trim())) {
              headerRowIdx = r;
              break;
            }
          }
        }

        if (headerRowIdx === -1) {
          setHoldingsUploadError('Could not locate a Ticker or Symbol column in spreadsheet headers.');
          setUploadedHoldingRows([]);
          setHoldingIds([]);
          setIsLoading(false);
          return;
        }

        const headerRow = rawAoa[headerRowIdx].map((h, i) => String(h || '').trim() || `col_${i}`);
        const dataRowsAoa = rawAoa.slice(headerRowIdx + 1);

        const normalizedRows = [];
        for (const rowVals of dataRowsAoa) {
          if (!Array.isArray(rowVals) || !rowVals.some((c) => String(c).trim())) continue;
          const rowObj = {};
          headerRow.forEach((h, i) => {
            rowObj[h] = String(rowVals[i] !== undefined && rowVals[i] !== null ? rowVals[i] : '').trim();
          });
          if (Object.values(rowObj).some(Boolean)) {
            normalizedRows.push(rowObj);
          }
        }

        if (!normalizedRows.length) {
          setHoldingsUploadError('The selected spreadsheet does not contain any data rows.');
          setUploadedHoldingRows([]);
          setHoldingIds([]);
          setIsLoading(false);
          return;
        }

        setUploadedHoldingRows(normalizedRows);

        const rowHeaders = Object.keys(normalizedRows[0]);
        const identifierHeader = rowHeaders.find((header) => {
          const norm = header.toLowerCase().replace(/[^a-z0-9]/g, '');
          return TICKER_HEADER_CANDIDATES.includes(norm);
        });

        if (!identifierHeader) {
          setHoldingIds([]);
          setHoldingsUploadSummary(`${normalizedRows.length} rows loaded for review.`);
          setIsLoading(false);
          return;
        }

        const nameHeader = rowHeaders.find((h) =>
          ['securityname', 'name', 'company', 'companyname', 'description'].includes(
            h.toLowerCase().replace(/[^a-z0-9]/g, '')
          )
        );
        const sectorHeader = rowHeaders.find((h) =>
          ['sector', 'spsector', 'industry'].includes(h.toLowerCase().replace(/[^a-z0-9]/g, ''))
        );
        const exchangeHeader = rowHeaders.find((h) =>
          ['exchange', 'market'].includes(h.toLowerCase().replace(/[^a-z0-9]/g, ''))
        );
        const countryHeader = rowHeaders.find((h) =>
          ['country', 'countrycode', 'nation'].includes(h.toLowerCase().replace(/[^a-z0-9]/g, ''))
        );
        const rankHeader = rowHeaders.find((h) =>
          ['rank', 'holdingrank', 'position', '#'].includes(h.toLowerCase().replace(/[^a-z0-9]/g, ''))
        );

        const clientHoldings = normalizedRows.map((row, idx) => {
          const rawId = row[identifierHeader] || '';
          return {
            holding_id: `client-${rawId}-${idx}`,
            canonical_company_id: `comp-${rawId.toLowerCase()}`,
            ticker: rawId,
            name: (nameHeader && row[nameHeader]) || rawId,
            country: (countryHeader && row[countryHeader]) || 'US',
            exchange: (exchangeHeader && row[exchangeHeader]) || 'NYSE',
            sector: (sectorHeader && row[sectorHeader]) || 'General',
            shares: parseFloat(row['Shares'] || row['Quantity'] || 0) || 0,
            cost_basis: parseFloat(row['Cost'] || row['Price'] || 0) || 0,
            weight_pct: parseFloat(row['Weight'] || row['Allocation'] || 0) || 0,
            holding_rank: (rankHeader && parseInt(row[rankHeader], 10)) || idx + 1,
            portfolio_name: 'Core Equity Fund',
          };
        });

        setPersistentHoldings(clientHoldings);
        const ids = clientHoldings.map((h) => h.canonical_company_id || h.holding_id);
        setHoldingIds(ids);
        setHoldingsUploadSummary(`Loaded ${clientHoldings.length} holdings into portfolio.`);
      } catch (parseErr) {
        console.error('[useHoldingsImport] Fallback parser error:', parseErr);
        setHoldingsUploadError('The selected file could not be read. Use a valid CSV, XLS, or XLSX file.');
        setUploadedHoldingRows([]);
        setHoldingIds([]);
      } finally {
        setIsLoading(false);
      }
    };

    reader.onerror = () => {
      setHoldingsUploadError('The holdings file could not be read.');
      setIsLoading(false);
    };

    reader.readAsArrayBuffer(file);
  };

  // Merge holdings with active screening run results
  const displayedHoldings = persistentHoldings.length > 0
    ? persistentHoldings.map((ph) => {
        // Check if this holding is present in current screening run
        const screenedMatch = securities.find(
          (s) =>
            (s.id && ph.canonical_company_id && s.id === ph.canonical_company_id) ||
            (s.ticker && ph.ticker && s.ticker.toUpperCase() === ph.ticker.toUpperCase())
        );

        const holdingRank = ph.holding_rank ?? ph.holdingRank ?? null;

        if (screenedMatch) {
          const currentRank = screenedMatch.rank ?? null;
          const rankDelta = (currentRank !== null && holdingRank !== null) ? (holdingRank - currentRank) : null;

          const isTop20 = (screenedMatch.rank && screenedMatch.rank <= 20) || 
                          (screenedMatch.stageStatus === 'passed' && screenedMatch.rank <= 20);
          const isRankNearMiss = screenedMatch.nearMissStatus === 'rank_near_miss' || 
                                (screenedMatch.rank && screenedMatch.rank > 20 && screenedMatch.stageStatus === 'passed');
          const isExited = screenedMatch.stageStatus !== 'passed' || screenedMatch.deltaStatus === 'exited';

          let comparisonStatus = 'held_in_top20';
          let comparisonVerdict = `🏆 Top 20 (#${screenedMatch.rank})`;
          let recommendedAction = 'Keep';

          if (isExited) {
            comparisonStatus = 'held_exited';
            comparisonVerdict = '▼ Exited Model';
            recommendedAction = 'Drop';
          } else if (isRankNearMiss) {
            comparisonStatus = 'held_rank_miss';
            comparisonVerdict = `⚠️ Rank Near-Miss (#${screenedMatch.rank})`;
            recommendedAction = 'Review';
          }

          return {
            ...screenedMatch,
            shares: ph.shares,
            costBasis: ph.cost_basis,
            weightPct: ph.weight_pct,
            portfolioName: ph.portfolio_name,
            isHolding: true,
            holdingRank,
            currentRank,
            holdingRankDelta: rankDelta,
            rankDelta,
            comparisonStatus,
            comparisonVerdict,
            recommendedAction,
          };
        }

        // Return holding item with fallback display fields (Unscreened in current regional run)
        return {
          id: ph.canonical_company_id || ph.holding_id,
          name: ph.name || ph.ticker,
          ticker: ph.ticker,
          country: ph.country || 'US',
          exchange: ph.exchange || 'NYSE',
          sector: ph.sector || 'Unclassified',
          score: '—',
          rank: null,
          currentRank: null,
          holdingRank,
          holdingRankDelta: null,
          rankDelta: null,
          fwdPe: null,
          peg: null,
          evEbitda: null,
          shares: ph.shares,
          costBasis: ph.cost_basis,
          weightPct: ph.weight_pct,
          portfolioName: ph.portfolio_name,
          isHolding: true,
          comparisonStatus: 'held_unscreened',
          comparisonVerdict: '○ Unscreened in this Run',
          recommendedAction: 'Hold',
          stageStatus: 'holding',
          deltaStatus: 'unscreened',
        };
      })
    : [];

  const holdingTickerSet = new Set(
    (persistentHoldings || []).map((h) => h.ticker?.toUpperCase()).filter(Boolean)
  );

  // Top 20 model winners that the client DOES NOT currently own
  const buyCandidates = securities
    .filter(
      (s) =>
        ((s.rank && s.rank <= 20) || (s.stageStatus === 'passed' && s.rank <= 20)) &&
        !holdingTickerSet.has(s.ticker?.toUpperCase())
    )
    .map((s) => ({
      ...s,
      isBuyCandidate: true,
      currentRank: s.rank,
      holdingRank: null,
      holdingRankDelta: null,
      rankDelta: null,
      comparisonStatus: 'buy_candidate',
      comparisonVerdict: '★ Top 20 Buy Idea (Not Held)',
      recommendedAction: 'Buy',
    }));

  const top20HeldCount = displayedHoldings.filter((h) => h.comparisonStatus === 'held_in_top20').length;
  const rankMissHeldCount = displayedHoldings.filter((h) => h.comparisonStatus === 'held_rank_miss').length;
  const exitedHeldCount = displayedHoldings.filter((h) => h.comparisonStatus === 'held_exited').length;
  const unscreenedHeldCount = displayedHoldings.filter((h) => h.comparisonStatus === 'held_unscreened').length;

  return {
    holdings: displayedHoldings,
    persistentHoldings,
    buyCandidates,
    top20HeldCount,
    rankMissHeldCount,
    exitedHeldCount,
    unscreenedHeldCount,
    holdingTickerSet,
    uploadedHoldingRows,
    uploadHoldingsFile,
    clearPortfolioHoldings,
    holdingsUploadError,
    holdingsUploadSummary,
    isLoadingHoldings: isLoading,
    reloadHoldings: loadPersistentHoldings,
  };
};
