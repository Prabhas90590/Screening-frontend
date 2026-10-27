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
    changesSubTab,
    setChangesSubTab,
    nearMissSubTab,
    setNearMissSubTab,
    filterSector,
    setFilterSector,
    filterRegion,
    setFilterRegion,
    filterCap,
    setFilterCap,
    searchQuery,
    setSearchQuery,
    sectors,
    countries,
    securities,
  } = useScreening();

  const selectedCountries = countries.filter((country) => country.selected);
  const selectedSectors = sectors.filter((sector) => sector.selected);

  const top20Count = securities.filter(
    (s) => (s.stageStatus === 'passed' && s.rank <= 20) || (s.rank && s.rank <= 20 && s.deltaStatus !== 'exited')
  ).length || 20;

  const nearMissCount = securities.filter(
    (s) => s.nearMissStatus === 'rule_near_miss' || s.nearMissStatus === 'rank_near_miss' || s.deltaStatus === 'rule_miss'
  ).length;

  const enteredCount = securities.filter((s) => s.deltaStatus === 'entered').length;
  const exitedCount = securities.filter((s) => s.deltaStatus === 'exited').length;
  const totalChanges = enteredCount + exitedCount;

  const tabs = [
    { id: 'top20', label: `🏆 Top 20 (${top20Count})` },
    { id: 'nearMisses', label: `⚠️ Near Misses (${nearMissCount})` },
    { id: 'allScreened', label: `📋 All Evaluated (${securities.length})` },
    { id: 'changes', label: `🔄 Turnover (${enteredCount} In / ${exitedCount} Out)` },
    { id: 'myHoldings', label: '💼 My Holdings' },
  ];

  return (
    <div className="space-y-3">
      {/* 4 Clean Primary Tabs */}
      <div className="flex items-center justify-between border-b border-slate-200 overflow-x-auto pb-0.5">
        <div className="flex space-x-6 sm:space-x-8 shrink-0">
          {tabs.map((tab) => {
            const isActive = resultsTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setResultsTab(tab.id)}
                className={`pb-2.5 text-xs sm:text-sm font-semibold transition-colors border-b-2 -mb-[2px] cursor-pointer whitespace-nowrap ${
                  isActive
                    ? 'border-[#147b73] text-[#147b73]'
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
          className="mb-1.5 shrink-0 px-3 py-1.5 bg-[#e5a83b] hover:bg-[#d6982c] text-white text-xs font-semibold rounded-md shadow-2xs transition-colors cursor-pointer"
        >
          Export to Excel
        </button>
      </div>

      {/* Sub-pills when "Changes" is active */}
      {resultsTab === 'changes' && (
        <div className="flex items-center gap-2 pt-1 pb-0.5">
          <span className="text-xs text-slate-500 font-semibold mr-1">Filter Changes:</span>
          <button
            type="button"
            onClick={() => setChangesSubTab && setChangesSubTab('all')}
            className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer ${
              (changesSubTab || 'all') === 'all'
                ? 'bg-slate-800 text-white shadow-2xs'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            All Changes ({totalChanges})
          </button>
          <button
            type="button"
            onClick={() => setChangesSubTab && setChangesSubTab('entered')}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer ${
              changesSubTab === 'entered'
                ? 'bg-emerald-600 text-white shadow-2xs'
                : 'bg-emerald-50 text-emerald-800 border border-emerald-200/80 hover:bg-emerald-100'
            }`}
          >
            ▲ Entered Top 20 ({enteredCount})
          </button>
          <button
            type="button"
            onClick={() => setChangesSubTab && setChangesSubTab('exited')}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer ${
              changesSubTab === 'exited'
                ? 'bg-rose-600 text-white shadow-2xs'
                : 'bg-rose-50 text-rose-800 border border-rose-200/80 hover:bg-rose-100'
            }`}
          >
            ▼ Exited Top 20 ({exitedCount})
          </button>
        </div>
      )}

      {/* Sub-pills when "Near Misses" is active */}
      {resultsTab === 'nearMisses' && (
        <div className="flex items-center gap-2 pt-1 pb-0.5">
          <span className="text-xs text-slate-500 font-semibold mr-1">Near Miss Type:</span>
          <button
            type="button"
            onClick={() => setNearMissSubTab && setNearMissSubTab('all')}
            className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer ${
              (nearMissSubTab || 'all') === 'all'
                ? 'bg-slate-800 text-white shadow-2xs'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            All Near Misses
          </button>
          <button
            type="button"
            onClick={() => setNearMissSubTab && setNearMissSubTab('rank')}
            className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer ${
              nearMissSubTab === 'rank'
                ? 'bg-[#147b73] text-white shadow-2xs'
                : 'bg-teal-50 text-[#147b73] border border-teal-200 hover:bg-teal-100'
            }`}
          >
            Rank Cutoff (Ranks 21–40)
          </button>
          <button
            type="button"
            onClick={() => setNearMissSubTab && setNearMissSubTab('rule')}
            className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer ${
              nearMissSubTab === 'rule'
                ? 'bg-amber-600 text-white shadow-2xs'
                : 'bg-amber-50 text-amber-800 border border-amber-200 hover:bg-amber-100'
            }`}
          >
            Rule Threshold Near-Misses (&lt; 10%)
          </button>
        </div>
      )}

      {/* Holdings Upload Bar */}
      {resultsTab === 'myHoldings' && (
        <div className="flex flex-wrap items-center gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
          <label className="cursor-pointer rounded-md bg-[#147b73] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#0f675f]">
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
            <span className="text-[11px] font-medium text-[#147b73]">{holdingsUploadSummary}</span>
          )}
          {holdingsUploadError && (
            <span className="text-[11px] font-medium text-red-600">{holdingsUploadError}</span>
          )}
        </div>
      )}

      {/* Streamlined Filter Pills & Search */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs pt-1">
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Sector Filter */}
          <select
            value={filterSector}
            onChange={(e) => setFilterSector(e.target.value)}
            className="bg-white border border-slate-300 rounded-md px-2.5 py-1 text-slate-700 font-medium focus:outline-hidden focus:border-[#147b73] cursor-pointer"
          >
            <option value="All">All Sectors</option>
            {selectedSectors.length > 0 ? (
              selectedSectors.map((s) => (
                <option key={s.name} value={s.name}>
                  {s.name}
                </option>
              ))
            ) : (
              <>
                <option value="Info Tech">Info Tech</option>
                <option value="Financials">Financials</option>
                <option value="Health Care">Health Care</option>
                <option value="Cons. Staples">Cons. Staples</option>
                <option value="Energy">Energy</option>
                <option value="Materials">Materials</option>
                <option value="Comm.">Comm.</option>
                <option value="Utilities">Utilities</option>
              </>
            )}
          </select>

          {/* Region / Country Filter */}
          <select
            value={filterRegion}
            onChange={(e) => setFilterRegion(e.target.value)}
            className="bg-white border border-slate-300 rounded-md px-2.5 py-1 text-slate-700 font-medium focus:outline-hidden focus:border-[#147b73] cursor-pointer"
          >
            <option value="All">All Countries</option>
            {selectedCountries.length > 0 ? (
              selectedCountries.map((c) => (
                <option key={c.id} value={c.name}>
                  {c.name}
                </option>
              ))
            ) : (
              <>
                <option value="United States">United States</option>
                <option value="India">India</option>
                <option value="United Kingdom">United Kingdom</option>
                <option value="Netherlands">Netherlands</option>
                <option value="Taiwan">Taiwan</option>
                <option value="Switzerland">Switzerland</option>
                <option value="Germany">Germany</option>
                <option value="France">France</option>
                <option value="Norway">Norway</option>
              </>
            )}
          </select>

          {/* Cap Filter */}
          <select
            value={filterCap}
            onChange={(e) => setFilterCap(e.target.value)}
            className="bg-white border border-slate-300 rounded-md px-2.5 py-1 text-slate-700 font-medium focus:outline-hidden focus:border-[#147b73] cursor-pointer"
          >
            <option value="All">All Market Caps</option>
            <option value="Large">Large-cap</option>
            <option value="Mid">Mid-cap</option>
            <option value="Small">Small-cap</option>
          </select>
        </div>

        {/* Search Box */}
        <div className="w-56">
          <input
            type="text"
            placeholder="Search company or ticker..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white border border-slate-300 rounded-md px-3 py-1 text-slate-700 placeholder-slate-400 focus:outline-hidden focus:border-[#147b73]"
          />
        </div>
      </div>
    </div>
  );
};

