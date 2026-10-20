import React from 'react';
import { ScheduleConfigCard } from './ScheduleConfigCard';
import { NextRunsCard } from './NextRunsCard';
import { RunHistoryTable } from './RunHistoryTable';

export const ScheduleView = () => {
  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top 2 Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ScheduleConfigCard />
        </div>
        <div className="lg:col-span-1">
          <NextRunsCard />
        </div>
      </div>

      {/* Bottom Run History Card */}
      <div>
        <RunHistoryTable />
      </div>
    </div>
  );
};

