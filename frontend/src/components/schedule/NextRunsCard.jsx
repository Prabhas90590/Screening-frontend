import React from 'react';
import { useScreening } from '../../context/ScreeningContext';

export const NextRunsCard = () => {
  const { nextRuns, scheduleConfig } = useScreening();

  const isEnabled = scheduleConfig?.isEnabled ?? true;
  const frequency = scheduleConfig?.frequency || 'Daily';
  const dailyType = scheduleConfig?.dailyType || 'trading_days';
  const time = scheduleConfig?.time || '08:30';

  // Format runs
  const formattedRuns = (nextRuns && nextRuns.length > 0)
    ? nextRuns.map((r) => {
        try {
          const d = new Date(r);
          return d.toLocaleString('en-IN', {
            weekday: 'short',
            day: 'numeric',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true,
          }) + ' IST';
        } catch {
          return r;
        }
      })
    : [
        `Next trading day at ${time} IST`,
        `Upcoming day +1 at ${time} IST`,
        `Upcoming day +2 at ${time} IST`,
      ];

  return (
    <div className="bg-white rounded-lg border border-slate-200/80 p-6 shadow-2xs flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-slate-800">Next Scheduled Runs</h2>
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
              isEnabled
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-amber-50 text-amber-700 border border-amber-200'
            }`}
          >
            {isEnabled ? 'Active' : 'Paused'}
          </span>
        </div>

        <div className="space-y-3 font-mono text-xs text-slate-700">
          {formattedRuns.map((runDate, idx) => (
            <div
              key={idx}
              className="py-2 px-2.5 rounded border border-slate-100 bg-slate-50/50 flex items-center justify-between"
            >
              <div className="flex items-center space-x-2">
                <span className="h-2 w-2 rounded-full bg-[#146b63]" />
                <span className="font-semibold text-slate-800">{runDate}</span>
              </div>
              <span className="text-[10px] font-sans font-medium text-slate-400">
                {idx === 0 ? 'Next run' : `+${idx} cycle`}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="pt-6 space-y-2 border-t border-slate-100 mt-6 text-[11px] text-slate-500">
        <div className="flex items-center justify-between">
          <span>Cadence:</span>
          <span className="font-semibold text-slate-700">
            {frequency === 'Daily'
              ? dailyType === 'trading_days'
                ? 'Every Trading Day (Mon–Fri)'
                : 'Every Calendar Day'
              : frequency}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span>Time:</span>
          <span className="font-mono text-slate-700">
            {time && time.includes(':') ? (() => {
              const [hStr, mStr] = time.split(':');
              const h = parseInt(hStr, 10);
              const period = h >= 12 ? 'PM' : 'AM';
              const h12 = h % 12 === 0 ? 12 : h % 12;
              return `${String(h12).padStart(2, '0')}:${mStr} ${period} IST`;
            })() : `${time} IST`}
          </span>
        </div>
        <p className="text-[10px] text-slate-400 pt-1">
          ✓ Runs skip official exchange holidays when data is unchanged.
        </p>
      </div>
    </div>
  );
};
