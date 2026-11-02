import React from 'react';
import { useScreening } from '../../context/ScreeningContext';

// Computes exact upcoming timestamps matching active configuration (zero mock strings)
function computeExactUpcomingRuns(config, count = 3) {
  const timeStr = config?.time || '08:30';
  const parts = timeStr.split(':');
  const targetH = parseInt(parts[0], 10) || 8;
  const targetM = parseInt(parts[1], 10) || 30;

  const freq = (config?.frequency || 'Daily').toLowerCase();
  const dailyType = config?.dailyType || 'trading_days';
  const activeDays = (config?.activeDays || ['mon', 'tue', 'wed', 'thu', 'fri']).map((d) => d.toLowerCase());
  const dayIndexMap = { sun: 0, mon: 1, tue: 2, wed: 3, thu: 4, fri: 5, sat: 6 };
  const targetDayIndices = new Set(activeDays.map((d) => dayIndexMap[d]).filter((v) => v !== undefined));

  const runs = [];
  const now = new Date();
  const cursor = new Date(now);

  for (let i = 0; i < 90; i++) {
    const cand = new Date(cursor.getFullYear(), cursor.getMonth(), cursor.getDate(), targetH, targetM, 0, 0);
    let isValid = false;

    if (cand.getTime() > now.getTime()) {
      const dayOfWeek = cand.getDay(); // 0 is Sun, 6 is Sat

      if (freq === 'daily') {
        if (dailyType === 'trading_days') {
          isValid = dayOfWeek >= 1 && dayOfWeek <= 5;
        } else {
          isValid = true; // all_days
        }
      } else if (freq === 'weekly') {
        isValid = targetDayIndices.has(dayOfWeek);
      } else if (freq === 'monthly') {
        const dom = Math.min(Math.max(config?.dayOfMonth || 1, 1), 28);
        isValid = cand.getDate() === dom;
      } else {
        isValid = dayOfWeek >= 1 && dayOfWeek <= 5;
      }

      if (isValid) {
        runs.push(cand);
        if (runs.length >= count) break;
      }
    }
    cursor.setDate(cursor.getDate() + 1);
  }

  return runs;
}

export const NextRunsCard = () => {
  const { nextRuns, scheduleConfig } = useScreening();

  const isEnabled = scheduleConfig?.isEnabled ?? true;
  const frequency = scheduleConfig?.frequency || 'Daily';
  const dailyType = scheduleConfig?.dailyType || 'trading_days';
  const time = scheduleConfig?.time || '08:30';

  // Format runs using exact computed dates or backend dates
  let dateObjects = [];
  if (nextRuns && nextRuns.length > 0) {
    dateObjects = nextRuns.map((r) => new Date(r)).filter((d) => !isNaN(d.getTime()));
  }
  if (dateObjects.length === 0) {
    dateObjects = computeExactUpcomingRuns(scheduleConfig, 3);
  }

  const formattedRuns = dateObjects.map((d) => {
    return (
      d.toLocaleString('en-IN', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      }) + ' IST'
    );
  });

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
          {formattedRuns.length === 0 ? (
            <div className="py-3 px-3 text-center text-slate-400 text-xs font-sans">
              No upcoming scheduled runs found.
            </div>
          ) : (
            formattedRuns.map((runDate, idx) => (
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
            ))
          )}
        </div>
      </div>

      <div className="pt-6 space-y-2 border-t border-slate-100 mt-6 text-[11px] text-slate-500">
        <div className="flex items-center justify-between">
          <span>Cadence:</span>
          <span className="font-semibold text-slate-700">
            {frequency === 'Daily'
              ? dailyType === 'trading_days'
                ? 'Every Trading Day (Mon–Fri)'
                : 'Every Calendar Day (7 Days)'
              : frequency}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span>Time:</span>
          <span className="font-mono text-slate-700">
            {time && time.includes(':')
              ? (() => {
                  const [hStr, mStr] = time.split(':');
                  const h = parseInt(hStr, 10);
                  const period = h >= 12 ? 'PM' : 'AM';
                  const h12 = h % 12 === 0 ? 12 : h % 12;
                  return `${String(h12).padStart(2, '0')}:${mStr} ${period} IST`;
                })()
              : `${time} IST`}
          </span>
        </div>
        <p className="text-[10px] text-slate-400 pt-1">
          {dailyType === 'trading_days'
            ? '✓ Runs skip official exchange holidays when data is unchanged.'
            : '✓ Runs 7 days a week including market holidays.'}
        </p>
      </div>
    </div>
  );
};
