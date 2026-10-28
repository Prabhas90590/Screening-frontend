import { useState, useEffect, useCallback } from 'react';
import * as XLSX from 'xlsx';
import { fetchHoldings, uploadHoldingsFile as apiUploadHoldings } from '../../services/api';

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
      if (serverHoldings && Array.isArray(serverHoldings) && serverHoldings.length > 0) {
        setPersistentHoldings(serverHoldings);
        const ids = serverHoldings.map((h) => h.canonical_company_id || h.holding_id);
        setHoldingIds(ids);
        setHoldingsUploadSummary(`Active portfolio loaded (${serverHoldings.length} positions stored).`);
      }
    } catch (err) {
      console.warn('[useHoldingsImport] Could not load holdings from backend:', err);
    }
  }, []);

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
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json(firstSheet, { defval: '', raw: false });

        if (!rows.length) {
          setHoldingsUploadError('The selected spreadsheet does not contain any data rows.');
          setUploadedHoldingRows([]);
          setHoldingIds([]);
          setIsLoading(false);
          return;
        }

        const normalizedRows = rows.map((row) =>
          Object.fromEntries(
            Object.entries(row).map(([key, value]) => [key.trim(), String(value).trim()])
          )
        );
        setUploadedHoldingRows(normalizedRows);

        const rowHeaders = Object.keys(normalizedRows[0]);
        const identifierHeader = rowHeaders.find((header) =>
          ['ticker', 'symbol', 'security', 'security_id'].includes(header.toLowerCase())
        );

        if (!identifierHeader) {
          setHoldingIds([]);
          setHoldingsUploadSummary(`${normalizedRows.length} rows loaded for review.`);
          setIsLoading(false);
          return;
        }

        const identifiers = normalizedRows
          .map((row) => row[identifierHeader]?.toLowerCase())
          .filter(Boolean);

        const matchedIds = securities
          .filter(
            (security) =>
              identifiers.includes(security.ticker?.toLowerCase()) ||
              identifiers.includes(security.id?.toLowerCase())
          )
          .map((security) => security.id);

        const uniqueMatchedIds = [...new Set(matchedIds)];
        const unmatchedCount = identifiers.length - uniqueMatchedIds.length;

        setHoldingIds(uniqueMatchedIds);
        setHoldingsUploadSummary(
          `${normalizedRows.length} rows loaded; ${uniqueMatchedIds.length} matching result` +
            `${uniqueMatchedIds.length === 1 ? '' : 's'} found` +
            (unmatchedCount > 0 ? `; ${unmatchedCount} not matched.` : '.')
        );
      } catch {
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
            s.id === ph.canonical_company_id ||
            s.ticker?.toLowerCase() === ph.ticker?.toLowerCase()
        );

        if (screenedMatch) {
          return {
            ...screenedMatch,
            shares: ph.shares,
            costBasis: ph.cost_basis,
            weightPct: ph.weight_pct,
            portfolioName: ph.portfolio_name,
            isHolding: true,
          };
        }

        // Return holding item with fallback display fields
        return {
          id: ph.canonical_company_id || ph.holding_id,
          name: ph.name || ph.ticker,
          ticker: ph.ticker,
          country: ph.country || 'US',
          exchange: ph.exchange || 'NYSE',
          sector: ph.sector || 'Unclassified',
          score: '—',
          rank: '—',
          fwdPe: null,
          peg: null,
          evEbitda: null,
          shares: ph.shares,
          costBasis: ph.cost_basis,
          weightPct: ph.weight_pct,
          portfolioName: ph.portfolio_name,
          isHolding: true,
          stageStatus: 'holding',
          deltaStatus: 'retained',
        };
      })
    : securities.filter((security) => holdingIds.includes(security.id));

  return {
    holdings: displayedHoldings,
    persistentHoldings,
    uploadedHoldingRows,
    uploadHoldingsFile,
    holdingsUploadError,
    holdingsUploadSummary,
    isLoadingHoldings: isLoading,
    reloadHoldings: loadPersistentHoldings,
  };
};
