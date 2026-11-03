const fs = require('fs');

// 1. Update ScheduleConfigCard.jsx
let card = fs.readFileSync('frontend/src/components/schedule/ScheduleConfigCard.jsx', 'utf8');
card = card.replace(/\r\n/g, '\n');

const freqTarget = `                  onClick={() => {
                    // Switching cadence cancels edit mode of different frequency
                    const isDifferent = scheduleConfig?.scheduleId && scheduleConfig?.frequency !== freq;
                    updateScheduleConfig({
                      frequency: freq,
                      scheduleId: isDifferent ? '' : (scheduleConfig?.scheduleId || ''),
                    });
                  }}`;

const freqReplacement = `                  onClick={() => {
                    // Switching cadence cancels edit mode of different frequency
                    const isDifferent = scheduleConfig?.scheduleId && scheduleConfig?.frequency !== freq;
                    let nextDays = scheduleConfig?.activeDays;
                    if (freq === 'Daily') {
                      if (!nextDays || nextDays.length <= 1) {
                        nextDays = (scheduleConfig?.dailyType === 'all_days')
                          ? ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
                          : ['mon', 'tue', 'wed', 'thu', 'fri'];
                      }
                    } else if (freq === 'Weekly') {
                      if (!nextDays || nextDays.length > 2) {
                        nextDays = ['mon'];
                      }
                    }
                    updateScheduleConfig({
                      frequency: freq,
                      activeDays: nextDays,
                      scheduleId: isDifferent ? '' : (scheduleConfig?.scheduleId || ''),
                    });
                  }}`;

if (card.includes(freqTarget)) {
  card = card.replace(freqTarget, freqReplacement);
  console.log('Updated frequency switcher in ScheduleConfigCard.jsx');
} else {
  console.log('WARNING: freqTarget not found in ScheduleConfigCard.jsx');
}

// Update dailyType radio inputs and add Active Days pills in Daily
const dailyTypeTarget = `            {/* Daily Type */}
            <div className="grid grid-cols-4 items-center gap-4">
              <label className="text-slate-600 font-medium">Run On</label>
              <div className="col-span-3 flex items-center space-x-4">
                <label className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="radio"
                    name="dailyType"
                    value="trading_days"
                    checked={dailyType === 'trading_days'}
                    onChange={() => updateScheduleConfig({ dailyType: 'trading_days' })}
                    className="accent-[#146b63]"
                  />
                  <span className="font-medium">Every Trading Day (Mon–Fri)</span>
                </label>
                <label className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="radio"
                    name="dailyType"
                    value="all_days"
                    checked={dailyType === 'all_days'}
                    onChange={() => updateScheduleConfig({ dailyType: 'all_days' })}
                    className="accent-[#146b63]"
                  />
                  <span>Every Calendar Day (7 Days)</span>
                </label>
              </div>
            </div>`;

const dailyTypeReplacement = `            {/* Daily Type */}
            <div className="grid grid-cols-4 items-center gap-4">
              <label className="text-slate-600 font-medium">Run On</label>
              <div className="col-span-3 flex items-center space-x-4">
                <label className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="radio"
                    name="dailyType"
                    value="trading_days"
                    checked={dailyType === 'trading_days'}
                    onChange={() =>
                      updateScheduleConfig({
                        dailyType: 'trading_days',
                        activeDays: ['mon', 'tue', 'wed', 'thu', 'fri'],
                      })
                    }
                    className="accent-[#146b63]"
                  />
                  <span className="font-medium">Every Trading Day (Mon–Fri)</span>
                </label>
                <label className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="radio"
                    name="dailyType"
                    value="all_days"
                    checked={dailyType === 'all_days'}
                    onChange={() =>
                      updateScheduleConfig({
                        dailyType: 'all_days',
                        activeDays: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'],
                      })
                    }
                    className="accent-[#146b63]"
                  />
                  <span>Every Calendar Day (7 Days)</span>
                </label>
              </div>
            </div>

            {/* Daily Active Days (Visual selector & toggler) */}
            <div className="grid grid-cols-4 items-center gap-4">
              <label className="text-slate-600 font-medium">Active Days</label>
              <div className="col-span-3 flex flex-wrap items-center gap-2">
                {(dailyType === 'all_days'
                  ? [
                      { id: 'mon', label: 'Mon' },
                      { id: 'tue', label: 'Tue' },
                      { id: 'wed', label: 'Wed' },
                      { id: 'thu', label: 'Thu' },
                      { id: 'fri', label: 'Fri' },
                      { id: 'sat', label: 'Sat' },
                      { id: 'sun', label: 'Sun' },
                    ]
                  : daysOfWeek
                ).map((day) => {
                  const isSelected = (scheduleConfig.activeDays || []).includes(day.id);
                  return (
                    <button
                      key={day.id}
                      type="button"
                      onClick={() => toggleDay(day.id)}
                      className={\`px-3 py-1 rounded text-xs font-semibold flex items-center justify-center transition-colors cursor-pointer \${
                        isSelected
                          ? 'bg-[#146b63] text-white shadow-xs'
                          : 'bg-white border border-slate-300 text-slate-500 hover:bg-slate-100'
                      }\`}
                      title={\`Toggle \${day.label}\`}
                    >
                      {day.label}
                    </button>
                  );
                })}
                <span className="text-[11px] text-slate-400">
                  {dailyType === 'trading_days' ? '(Mon–Fri)' : '(7 Days / Week)'}
                </span>
              </div>
            </div>`;

if (card.includes(dailyTypeTarget)) {
  card = card.replace(dailyTypeTarget, dailyTypeReplacement);
  console.log('Updated dailyType and added active days pills in ScheduleConfigCard.jsx');
} else {
  console.log('WARNING: dailyTypeTarget not found in ScheduleConfigCard.jsx');
}

fs.writeFileSync('frontend/src/components/schedule/ScheduleConfigCard.jsx', card, 'utf8');

// 2. Update ScreeningContext.jsx
let ctx = fs.readFileSync('frontend/src/context/ScreeningContext.jsx', 'utf8');
ctx = ctx.replace(/\r\n/g, '\n');

const ctxTarget = `    const payload = {
      schedule_id: schedId,
      profile_id: merged.selectedProfileId || undefined,
      profile_name: merged.profile || 'Default Strategy',
      frequency: merged.frequency || 'Daily',
      daily_type: merged.dailyType || 'trading_days',
      active_days: merged.activeDays || ['mon', 'tue', 'wed', 'thu', 'fri'],`;

const ctxReplacement = `    let actDays = merged.activeDays;
    if ((merged.frequency || '').toLowerCase() === 'daily') {
      if (!actDays || !Array.isArray(actDays) || actDays.length === 0 || (actDays.length === 1 && actDays[0] === 'mon' && !merged.scheduleId)) {
        actDays = merged.dailyType === 'all_days'
          ? ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
          : ['mon', 'tue', 'wed', 'thu', 'fri'];
      }
    }

    const payload = {
      schedule_id: schedId,
      profile_id: merged.selectedProfileId || undefined,
      profile_name: merged.profile || 'Default Strategy',
      frequency: merged.frequency || 'Daily',
      daily_type: merged.dailyType || 'trading_days',
      active_days: actDays || ['mon', 'tue', 'wed', 'thu', 'fri'],`;

if (ctx.includes(ctxTarget)) {
  ctx = ctx.replace(ctxTarget, ctxReplacement);
  console.log('Updated saveScheduleToBackend activeDays logic in ScreeningContext.jsx');
} else {
  console.log('WARNING: ctxTarget not found in ScreeningContext.jsx');
}

fs.writeFileSync('frontend/src/context/ScreeningContext.jsx', ctx, 'utf8');

