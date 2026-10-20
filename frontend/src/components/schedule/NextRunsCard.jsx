import React from 'react';

export const NextRunsCard = () => {
  const nextRuns = [
    'Mon 5 Oct 2026, 06:00',
    'Mon 12 Oct 2026, 06:00',
    'Mon 19 Oct 2026, 06:00',
    'Mon 26 Oct 2026, 06:00',
  ];

  return (
    <div className="bg-white rounded-lg border border-slate-200/80 p-6 shadow-2xs flex flex-col justify-between">
      <div>
        <h2 className="text-base font-bold text-slate-800 mb-4">Next runs</h2>
        <div className="space-y-3 font-mono text-xs text-slate-700">
          {nextRuns.map((runDate, idx) => (
            <div key={idx} className="py-1 border-b border-slate-100 last:border-none">
              {runDate}
            </div>
          ))}
        </div>
      </div>

      <div className="pt-6 text-[11px] text-slate-400">
        Runs skip market holidays when data is unchanged.
      </div>
    </div>
  );
};

