import React from 'react';
import { useScreening } from '../../context/ScreeningContext';

export const ResultsFilterBar = ({
  uploadHoldingsFile,
  holdingsUploadError,
  holdingsUploadSummary,
  exportResults,
}) => {
  const {
    resultsTab,
    setResultsTab,
    filterSector,
    setFilterSector,
    filterRegion,
    setFilterRegion,
    filterCap,
    setFilterCap,
    searchQuery,
    setSearchQuery,
    funnelState,
    sectors,
    countries,
  } = useScreening();

  const selectedCountries = countries.filter((country) => country.selected);
  const selectedSectors = sectors.filter((sector) => sector.selected);

  const tabs = [
    { id: 'top20', label: 'Top 20' },
    { id: 'rankNearMisses', label: 'Near misses (21–40)' },
    { id: 'ruleNearMisses', label: 'Near misses (rules)' },
    { id: 'myHoldings', label: 'My holdings' },
    { id: 'allScreened', label: 'All screened' },
  ];

  return (
    <div className="space-y-4">
      {/* Subtabs */}
      <div className="flex items-center border-b border-slate-200">
        <div className="flex space-x-8">
          {tabs.map((tab) => {
            const isActive = resultsTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setResultsTab(tab.id)}
                className={`pb-2.5 text-sm font-semibold transition-colors border-b-2 -mb-[1px] ${
                  isActive
                    ? 'border-[#146b63] text-[#146b63]'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
        <button
          onClick={exportResults}
          className="ml-auto mb-2 px-4 py-1.5 bg-[#e5a83b] hover:bg-[#d6982c] text-white text-xs font-semibold rounded-md shadow-2xs transition-colors"
        >
          Export to Excel
        </button>
      </div>

      {resultsTab === 'myHoldings' && (
        <div className="flex flex-wrap items-center gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
          <label className="cursor-pointer rounded-md bg-[#146b63] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#0f5b54]">
            Upload holdings file
            <input
              type="file"
              accept=".csv,.xls,.xlsx,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              className="hidden"
              onChange={(event) => {
                uploadHoldingsFile(event.target.files?.[0]);
                event.target.value = '';
              }}
            />
          </label>
          <span className="text-[11px] text-slate-500">
            Supported files: CSV, XLS, XLSX
          </span>
          {holdingsUploadSummary && (
            <span className="text-[11px] font-medium text-[#146b63]">{holdingsUploadSummary}</span>
          )}
          {holdingsUploadError && (
            <span className="text-[11px] font-medium text-red-600">{holdingsUploadError}</span>
          )}
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-3">
          {/* Sector Filter */}
          <div className="relative">
            <select
              value={filterSector}
              onChange={(e) => setFilterSector(e.target.value)}
              className="bg-white border border-slate-300 rounded px-2.5 py-1.5 text-slate-700 font-medium pr-7 focus:outline-hidden focus:border-[#146b63]"
            >
              <option value="All">Sector: All</option>
              {selectedSectors.map((sector) => (
                <option key={sector.name} value={sector.name}>
                  Sector: {sector.name}
                </option>
              ))}
            </select>
          </div>

          {/* Country Filter */}
          <div className="relative">
            <select
              value={filterRegion}
              onChange={(e) => setFilterRegion(e.target.value)}
              className="bg-white border border-slate-300 rounded px-2.5 py-1.5 text-slate-700 font-medium pr-7 focus:outline-hidden focus:border-[#146b63]"
            >
              <option value="All">Country: All</option>
              {selectedCountries.map((country) => (
                <option key={country.id} value={country.name}>
                  Country: {country.name}
                </option>
              ))}
            </select>
          </div>

          {/* Cap Filter */}
          <div className="relative">
            <select
              value={filterCap}
              onChange={(e) => setFilterCap(e.target.value)}
              className="bg-white border border-slate-300 rounded px-2.5 py-1.5 text-slate-700 font-medium pr-7 focus:outline-hidden focus:border-[#146b63]"
            >
              <option value="All">Cap: All</option>
              <option value="Large">Cap: Large-cap</option>
              <option value="Mid">Cap: Mid-cap</option>
              <option value="Small">Cap: Small-cap</option>
            </select>
          </div>

          {/* Search Input */}
          <div className="w-56">
            <input
              type="text"
              placeholder="Search name or ticker"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded px-3 py-1.5 text-slate-700 placeholder-slate-400 focus:outline-hidden focus:border-[#146b63]"
            />
          </div>
        </div>

        {/* Run Metadata */}
        <div className="text-slate-500 font-mono text-[11px]">
          Run #{funnelState.runInfo.runNumber} · {funnelState.runInfo.profile} · {funnelState.runInfo.asOfDate}
        </div>
      </div>
    </div>
  );
};
