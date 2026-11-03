import React, { useState } from 'react';
import { useScreening } from '../../context/ScreeningContext';

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
        isValid = dailyType === 'trading_days' ? (dayOfWeek >= 1 && dayOfWeek <= 5) : true;
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
  const {
    nextRuns,
    nextRunsDetailed = [],
    nextRunsByFrequency = {},
    allSchedules = [],
    scheduleConfig,
  } = useScreening();

  const [frequencyFilter, setFrequencyFilter] = useState('all'); // 'all' | 'daily' | 'weekly' | 'monthly' | 'custom'

  const isEnabled = scheduleConfig?.isEnabled ?? true;

  // Filter detailed items based on selected frequency (strictly from actual schedules)
  let displayedItems = [];
  if (!allSchedules || allSchedules.length === 0) {
    displayedItems = [];
  } else if (frequencyFilter === 'all') {
    if (nextRunsDetailed && nextRunsDetailed.length > 0) {
      displayedItems = nextRunsDetailed;
    } else if (nextRuns && nextRuns.length > 0) {
      displayedItems = nextRuns.map((r) => ({
        datetime: r,
        schedule_id: allSchedules[0]?.schedule_id,
        frequency: allSchedules[0]?.frequency || 'Daily',
        time_of_day: allSchedules[0]?.time_of_day || '08:30',
        profile_name: allSchedules[0]?.profile_name || 'Strategy',
        label: `${allSchedules[0]?.frequency || 'Daily'} @ ${allSchedules[0]?.time_of_day || '08:30'}`,
        notification_email: allSchedules[0]?.notification_email || '',
        timezone: allSchedules[0]?.timezone || 'Asia/Kolkata',
      }));
    }
  } else {
    const targetFreq = frequencyFilter.toLowerCase();
    if (nextRunsDetailed && nextRunsDetailed.length > 0) {
      displayedItems = nextRunsDetailed.filter(
        (item) => (item.frequency || '').toLowerCase() === targetFreq
      );
    }
  }

  // Count active schedules by frequency
  const dailySchedules = allSchedules.filter((s) => (s.frequency || '').toLowerCase() === 'daily');
  const weeklySchedules = allSchedules.filter((s) => (s.frequency || '').toLowerCase() === 'weekly');
  const monthlySchedules = allSchedules.filter((s) => (s.frequency || '').toLowerCase() === 'monthly');
  const customSchedules = allSchedules.filter((s) => (s.frequency || '').toLowerCase() === 'custom');

  return (
    <div className="bg-white rounded-lg border border-slate-200/80 p-6 shadow-2xs flex flex-col justify-between h-full space-y-4">
      <div>
        {/* Header with Title, Status & Frequency Dropdown */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
          <div className="flex items-center space-x-2">
            <h2 className="text-base font-bold text-slate-800">Next Scheduled Runs</h2>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                isEnabled
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-amber-50 text-amber-700 border border-amber-200'
              }`}
            >
              {allSchedules.length > 0 ? `${allSchedules.length} Active` : isEnabled ? 'Active' : 'Paused'}
            </span>
          </div>

          {/* Cadence Selector Dropdown */}
          <div className="flex items-center space-x-1.5">
            <span className="text-[11px] text-slate-400 font-medium">Cadence:</span>
            <select
              value={frequencyFilter}
              onChange={(e) => setFrequencyFilter(e.target.value)}
              className="text-xs bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded px-2.5 py-1 font-semibold text-slate-700 cursor-pointer focus:outline-hidden focus:border-[#146b63] transition-colors"
              title="Filter upcoming execution runs by schedule frequency"
            >
              <option value="all">All Schedules ({allSchedules.length || 1})</option>
              <option value="daily">Daily Runs ({dailySchedules.length || (scheduleConfig?.frequency === 'Daily' ? 1 : 0)})</option>
              <option value="weekly">Weekly Runs ({weeklySchedules.length || (scheduleConfig?.frequency === 'Weekly' ? 1 : 0)})</option>
              <option value="monthly">Monthly Runs ({monthlySchedules.length || (scheduleConfig?.frequency === 'Monthly' ? 1 : 0)})</option>
              <option value="custom">Custom Runs ({customSchedules.length || (scheduleConfig?.frequency === 'Custom' ? 1 : 0)})</option>
            </select>
          </div>
        </div>

        {/* List of upcoming run datetimes */}
        <div className="space-y-2.5 font-mono text-xs text-slate-700">
          {displayedItems.length === 0 ? (
            <div className="py-6 px-3 text-center text-slate-400 text-xs font-sans rounded border border-slate-100 bg-slate-50/50">
              {allSchedules.length === 0
                ? 'No automated schedules configured. Create a schedule on the left to start automated screening.'
                : `No upcoming scheduled runs found for ${frequencyFilter === 'all' ? 'any schedule' : `${frequencyFilter} cadence`}.`}
            </div>
          ) : (
            displayedItems.slice(0, 6).map((item, idx) => {
              const d = new Date(item.datetime);
              const formattedDate = !isNaN(d.getTime())
                ? d.toLocaleString('en-IN', {
                    weekday: 'short',
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: true,
                  }) + ' IST'
                : item.datetime;

              return (
                <div
                  key={`${item.schedule_id}-${idx}`}
                  className="py-2.5 px-3 rounded border border-slate-100 bg-slate-50/60 hover:bg-slate-50 transition-colors flex items-center justify-between"
                >
                  <div className="flex items-center space-x-2.5">
                    <span className="h-2 w-2 rounded-full bg-[#146b63]" />
                    <div>
                      <span className="font-semibold text-slate-800 block">{formattedDate}</span>
                      <span className="text-[10px] font-sans text-slate-500 font-medium block">
                        {item.label || `${item.frequency} @ ${item.time_of_day} IST`}
                      </span>
                    </div>
                  </div>
                  <span className="text-[10px] font-sans font-medium px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-500 shrink-0">
                    {idx === 0 ? 'Next run' : `+${idx} cycle`}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Footer summary with Active Cadences */}
      <div className="pt-4 border-t border-slate-100 text-[11px] text-slate-500 space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Configured Schedules:</span>
          <span className="font-semibold text-slate-700">
            {allSchedules.length > 0
              ? `${allSchedules.length} active (${allSchedules.map((s) => `${s.frequency} ${s.time_of_day}`).join(', ')})`
              : 'None active'}
          </span>
        </div>
        <p className="text-[10px] text-slate-400">
          ✓ All background schedules fire independently and execute automatically via the scheduler daemon.
        </p>
      </div>
    </div>
  );
};
