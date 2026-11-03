const fs = require('fs');

let p = 'frontend/src/components/schedule/RunHistoryTable.jsx';
let content = fs.readFileSync(p, 'utf8').replace(/\r\n/g, '\n');

// 1. Destructure removeDayFromSchedule from useScreening()
content = content.replace(
  'clearAllRunsFromBackend,\n',
  'clearAllRunsFromBackend,\n    removeDayFromSchedule,\n'
);

// 2. Add cadenceFilter state and counts and handleDeleteForecastDay
const targetBeforeHandlers = `  const handleDeleteRun = async (runId, runLabel) => {`;

const newHandlers = `  const [cadenceFilter, setCadenceFilter] = useState('all'); // 'all' | 'daily' | 'weekly' | 'monthly' | 'custom'

  const dailySchedules = (allSchedules || []).filter((s) => (s.frequency || '').toLowerCase() === 'daily');
  const weeklySchedules = (allSchedules || []).filter((s) => (s.frequency || '').toLowerCase() === 'weekly');
  const monthlySchedules = (allSchedules || []).filter((s) => (s.frequency || '').toLowerCase() === 'monthly');
  const customSchedules = (allSchedules || []).filter((s) => (s.frequency || '').toLowerCase() === 'custom');

  const displayedSchedules = cadenceFilter === 'all'
    ? (allSchedules || [])
    : (allSchedules || []).filter((s) => (s.frequency || '').toLowerCase() === cadenceFilter);

  const handleDeleteForecastDay = async (schedId, dayKey, dayLabel, freq) => {
    const confirmed = window.confirm(
      \`Delete \${dayLabel} from this \${freq || 'Daily'} schedule?\\n\\nThis will remove \${dayLabel} from the schedule's active days. The schedule will continue running on all other days without deleting the whole schedule.\`
    );
    if (confirmed && removeDayFromSchedule) {
      await removeDayFromSchedule(schedId, dayKey);
    }
  };

  const handleDeleteRun = async (runId, runLabel) => {`;

content = content.replace(targetBeforeHandlers, newHandlers);

// 3. In the Configured Schedules section, add Cadence filter buttons and use displayedSchedules
const oldConfiguredSchedulesBlock = `          {/* 1. ACTIVE SCHEDULES (Each schedule is an independent entry in DB) */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <span>⏰</span>
                <span>Configured Schedules ({allSchedules.length})</span>
              </h3>
              <span className="text-[11px] text-slate-400">
                Each schedule runs independently; deleting one does not affect others.
              </span>
            </div>

            <div className="overflow-x-auto border border-slate-200/80 rounded-md">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    <th className="py-2.5 px-3">Cadence & Time</th>
                    <th className="py-2.5 px-3">Strategy Profile</th>
                    <th className="py-2.5 px-3">Recipients</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {allSchedules.length === 0 ? (
                    <tr>
                      <td colSpan="5" className="py-8 text-center text-slate-400">
                        No active schedules configured. Use the schedule configuration card above and click <strong>+ Save New Schedule</strong>.
                      </td>
                    </tr>
                  ) : (
                    allSchedules.map((s) => {`;

const newConfiguredSchedulesBlock = `          {/* 1. ACTIVE SCHEDULES (Each schedule is an independent entry in DB) */}
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
              <div className="flex items-center space-x-2">
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <span>⏰</span>
                  <span>Configured Schedules ({allSchedules.length})</span>
                </h3>
              </div>

              {/* Cadence Filter Tabs: All, Daily, Weekly, Monthly, Custom */}
              <div className="flex items-center space-x-1 bg-slate-100 p-0.5 rounded-md text-xs font-semibold">
                {[
                  { id: 'all', label: 'All', count: (allSchedules || []).length },
                  { id: 'daily', label: 'Daily', count: dailySchedules.length },
                  { id: 'weekly', label: 'Weekly', count: weeklySchedules.length },
                  { id: 'monthly', label: 'Monthly', count: monthlySchedules.length },
                  { id: 'custom', label: 'Custom', count: customSchedules.length },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setCadenceFilter(tab.id)}
                    className={\`px-2.5 py-1 rounded transition-colors cursor-pointer \${
                      cadenceFilter === tab.id
                        ? 'bg-white text-slate-900 shadow-2xs font-bold'
                        : 'text-slate-600 hover:text-slate-900'
                    }\`}
                  >
                    {tab.label} ({tab.count})
                  </button>
                ))}
              </div>
            </div>

            <div className="overflow-x-auto border border-slate-200/80 rounded-md">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    <th className="py-2.5 px-3">Cadence & Time</th>
                    <th className="py-2.5 px-3">Strategy Profile</th>
                    <th className="py-2.5 px-3">Active Days / Recurrence</th>
                    <th className="py-2.5 px-3">Recipients</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {displayedSchedules.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="py-8 text-center text-slate-400">
                        No \${cadenceFilter === 'all' ? '' : cadenceFilter} schedules configured. Configure your settings above and click <strong>+ Save New Schedule</strong>.
                      </td>
                    </tr>
                  ) : (
                    displayedSchedules.map((s) => {`;

content = content.replace(oldConfiguredSchedulesBlock, newConfiguredSchedulesBlock);

// 4. In the map of displayedSchedules, add the Active Days / Recurrence column
const oldRowCells = `                          <td className="py-3 px-3 text-slate-700 font-medium">
                            {s.profile_name || 'Default Strategy'}
                          </td>
                          <td className="py-3 px-3">
                            {emails.length === 0 ? (`;

const newRowCells = `                          <td className="py-3 px-3 text-slate-700 font-medium">
                            {s.profile_name || 'Default Strategy'}
                          </td>
                          <td className="py-3 px-3">
                            <div className="flex flex-wrap gap-1">
                              {(s.active_days || ['mon', 'tue', 'wed', 'thu', 'fri']).map((day) => (
                                <span
                                  key={day}
                                  className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-700 uppercase"
                                >
                                  {day}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="py-3 px-3">
                            {emails.length === 0 ? (`;

content = content.replace(oldRowCells, newRowCells);

// 5. In Execution Forecast Cycles table, add Day action button
const oldForecastStatusCell = `                          <td className="py-2.5 px-3 text-right">
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Armed
                            </span>
                          </td>`;

const newForecastStatusCell = `                          <td className="py-2.5 px-3 text-right">
                            {(() => {
                              const cycleDate = new Date(item.datetime || item);
                              const dayShort = !isNaN(cycleDate.getTime())
                                ? cycleDate.toLocaleString('en-US', { weekday: 'short' })
                                : '';
                              const dayKey = dayShort.toLowerCase();

                              return (
                                <div className="flex items-center justify-end space-x-2">
                                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                    Armed
                                  </span>
                                  {dayKey && (
                                    <button
                                      type="button"
                                      onClick={() => handleDeleteForecastDay(item.schedule_id, dayKey, dayShort, item.frequency)}
                                      className="px-2 py-0.5 text-[11px] font-semibold text-rose-600 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded transition-colors cursor-pointer"
                                      title={\`Delete \${dayShort} from this schedule (remaining days continue running)\`}
                                    >
                                      🗑️ Delete \${dayShort}
                                    </button>
                                  )}
                                </div>
                              );
                            })()}
                          </td>`;

content = content.replace(oldForecastStatusCell, newForecastStatusCell);

fs.writeFileSync(p, content.replace(/\n/g, '\r\n'), 'utf8');
console.log('RunHistoryTable.jsx updated with cadence filters and single-day deletion.');

