import React from 'react';
import { ResultsSummaryCards } from './ResultsSummaryCards';
import { ResultsFilterBar } from './ResultsFilterBar';
import { ResultsTable } from './ResultsTable';
import { SecurityDetailDrawer } from './SecurityDetailDrawer';
import { ResultsLegend } from './ResultsLegend';
import { useHoldingsImport } from './useHoldingsImport';
import { exportResultsToExcel } from './exportResults';
import { syncDecisionsApi } from '../../services/api';
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

  // Phase 16: Bulk sync decisions to PostgreSQL with profile_name and company_name upon Excel export
  const handleExportWithSync = async () => {
    const decisionsToSync = (securities || [])
      .filter((s) => s.decision === 'keep' || s.decision === 'drop')
      .map((s) => ({
        canonical_company_id: s.id,
        company_name: s.name,
        profile_name: activeProfileName,
        decision: s.decision,
        decision_reason: s.decisionReason || '',
        decision_note: s.decisionNote || '',
        run_id: currentRun?.id || null,
      }));

    if (decisionsToSync.length > 0) {
      try {
        await syncDecisionsApi({
          profile_name: activeProfileName,
          run_id: currentRun?.id || null,
          decisions: decisionsToSync,
        });
      } catch (err) {
        console.warn('[ResultsView] Could not sync decisions to DB on export:', err);
      }
    }

    // Trigger Excel download with Category, Rank, Decision, Decision Reason, etc.
    exportResultsToExcel(securities, activeProfileName);
  };

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
          exportResults={handleExportWithSync}
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
      {selectedSecurity && <SecurityDetailDrawer {...holdingsImport} />}
    </div>
  );
};
