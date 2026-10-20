import React from 'react';
import { ResultsFilterBar } from './ResultsFilterBar';
import { FunnelPipeline } from './FunnelPipeline';
import { ResultsTable } from './ResultsTable';
import { SecurityDetailDrawer } from './SecurityDetailDrawer';
import { ResultsLegend } from './ResultsLegend';
import { useHoldingsImport } from './useHoldingsImport';
import { exportResultsToCsv } from './exportResults';
import { useScreening } from '../../context/ScreeningContext';

export const ResultsView = () => {
  const { selectedSecurity, resultsTab, securities } = useScreening();
  const holdingsImport = useHoldingsImport(securities);

  return (
    <div className="flex h-full overflow-hidden">
      {/* Main Table Content */}
      <div className="flex-1 p-8 overflow-y-auto space-y-5">
        <ResultsFilterBar
          {...holdingsImport}
          exportResults={() => exportResultsToCsv(securities)}
        />
        {resultsTab !== 'myHoldings' && <FunnelPipeline />}
        <ResultsTable {...holdingsImport} />
        <ResultsLegend />
      </div>

      {/* Slide-over Inspector Drawer */}
      {selectedSecurity && <SecurityDetailDrawer />}
    </div>
  );
};
