import React from 'react';
import { ResultsSummaryCards } from './ResultsSummaryCards';
import { ResultsFilterBar } from './ResultsFilterBar';
import { ResultsTable } from './ResultsTable';
import { SecurityDetailDrawer } from './SecurityDetailDrawer';
import { ResultsLegend } from './ResultsLegend';
import { useHoldingsImport } from './useHoldingsImport';
import { exportResultsToExcel } from './exportResults';
import { useScreening } from '../../context/ScreeningContext';

export const ResultsView = () => {
  const { selectedSecurity, resultsTab, securities, currentRun, activeProfile } = useScreening();
  const [holdingsSubTab, setHoldingsSubTab] = React.useState('all');
  const holdingsImport = useHoldingsImport(securities);

  const activeProfileName =
    currentRun?.rules ||
    (activeProfile
      ? `${activeProfile.name}${activeProfile.versionNumber ? ` v${activeProfile.versionNumber}` : ''}`
      : 'Core Strategy');

  return (
    <div className="flex h-full overflow-hidden">
      {/* Main Table Content */}
      <div className="flex-1 p-6 md:p-8 overflow-y-auto space-y-4">
        {/* 1. Modern 3-Card Summary, Turnover & Strategy Comparison Header */}
        <ResultsSummaryCards />

        {/* 2. 4 Clean Tabs (Top 20, Changes, Near Misses, My Holdings) & Sub-Pills */}
        <ResultsFilterBar
          {...holdingsImport}
          holdingsSubTab={holdingsSubTab}
          setHoldingsSubTab={setHoldingsSubTab}
          exportResults={() => exportResultsToExcel(securities, activeProfileName)}
        />

        {/* 3. Streamlined 7-Column Results Table */}
        <ResultsTable
          {...holdingsImport}
          holdingsSubTab={holdingsSubTab}
        />

        {/* 4. Results Legend / Footnote */}
        <ResultsLegend />
      </div>

      {/* 5. Slide-Over Inspector Drawer with 16-Metric Breakdown & Before vs After comparison */}
      {selectedSecurity && <SecurityDetailDrawer />}
    </div>
  );
};
