import { useState } from 'react';
import * as XLSX from 'xlsx';

export const useHoldingsImport = (securities) => {
  const [holdingIds, setHoldingIds] = useState([]);
  const [holdingsUploadError, setHoldingsUploadError] = useState('');
  const [holdingsUploadSummary, setHoldingsUploadSummary] = useState('');
  const [uploadedHoldingRows, setUploadedHoldingRows] = useState([]);

  const uploadHoldingsFile = (file) => {
    if (!file) return;

    setHoldingsUploadError('');
    setHoldingsUploadSummary('');

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const workbook = XLSX.read(event.target?.result, { type: 'array' });
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json(firstSheet, {
          defval: '',
          raw: false,
        });

        if (!rows.length) {
          setHoldingsUploadError('The selected spreadsheet does not contain any data rows.');
          setUploadedHoldingRows([]);
          setHoldingIds([]);
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
          return;
        }

        const identifiers = normalizedRows
          .map((row) => row[identifierHeader]?.toLowerCase())
          .filter(Boolean);
        const matchedIds = securities
          .filter((security) =>
            identifiers.includes(security.ticker.toLowerCase()) ||
            identifiers.includes(security.id.toLowerCase())
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
        setHoldingsUploadError(
          'The selected file could not be read. Use a valid CSV, XLS, or XLSX file.'
        );
        setUploadedHoldingRows([]);
        setHoldingIds([]);
      }
    };
    reader.onerror = () => {
      setHoldingsUploadError('The holdings file could not be read.');
    };
    reader.readAsArrayBuffer(file);
  };

  return {
    holdings: securities.filter((security) => holdingIds.includes(security.id)),
    uploadedHoldingRows,
    uploadHoldingsFile,
    holdingsUploadError,
    holdingsUploadSummary,
  };
};
