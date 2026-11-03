const fs = require('fs');

let rhtPath = 'frontend/src/components/schedule/RunHistoryTable.jsx';
let content = fs.readFileSync(rhtPath, 'utf8').replace(/\r\n/g, '\n');

// 1. Destructure deleteRunFromBackend and clearAllRunsFromBackend in useScreening()
content = content.replace(
  'deleteScheduleFromBackend,\n',
  'deleteScheduleFromBackend,\n    deleteRunFromBackend,\n    clearAllRunsFromBackend,\n'
);

// 2. Add handleDeleteRun and handleClearAllRuns
const targetHandlers = `  const handleDeleteUpcomingSchedule = async (scheduleId, label) => {
    const confirmed = window.confirm(
      \`Are you sure you want to delete the schedule "\${label}"?\\n\\nThis will remove it and cancel all future automated runs.\`
    );
    if (confirmed && deleteScheduleFromBackend) {
      await deleteScheduleFromBackend(scheduleId);
    }
  };`;

const newHandlers = `  const handleDeleteUpcomingSchedule = async (scheduleId, label) => {
    const confirmed = window.confirm(
      \`Are you sure you want to delete the schedule "\${label}"?\\n\\nThis will remove it and cancel all future automated runs.\`
    );
    if (confirmed && deleteScheduleFromBackend) {
      await deleteScheduleFromBackend(scheduleId);
    }
  };

  const handleDeleteRun = async (runId, runLabel) => {
    const confirmed = window.confirm(
      \`Are you sure you want to permanently delete run "\${runLabel || runId}" from the database?\\n\\nThis will delete the execution record, its screened securities, and funnel metrics.\`
    );
    if (confirmed && deleteRunFromBackend) {
      await deleteRunFromBackend(runId);
    }
  };

  const handleClearAllRuns = async () => {
    const confirmed = window.confirm(
      \`Are you sure you want to delete ALL \${runHistory.length} screening runs from the database?\\n\\nThis will permanently purge your run history and cannot be undone.\`
    );
    if (confirmed && clearAllRunsFromBackend) {
      await clearAllRunsFromBackend();
    }
  };`;

content = content.replace(targetHandlers, newHandlers);

// 3. In the Header: Add Clear All Runs button
const targetHeader = `<div className="flex items-center space-x-3">
          <h2 className="text-base font-bold text-slate-800">Screening Executions</h2>
          <span className="text-xs text-slate-400 font-normal">| Live Run History & Schedules</span>
        </div>`;

const newHeader = `<div className="flex items-center space-x-3">
          <h2 className="text-base font-bold text-slate-800">Screening Executions</h2>
          <span className="text-xs text-slate-400 font-normal">| Live Run History & Schedules</span>
          {runHistory.length > 0 && (activeTab === 'all' || activeTab === 'completed') && (
            <button
              type="button"
              onClick={handleClearAllRuns}
              className="text-[11px] text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 px-2 py-0.5 rounded transition-colors font-medium flex items-center gap-1 cursor-pointer"
              title="Permanently purge all screening run history from the database"
            >
              <span>🗑️</span>
              <span>Clear History ({runHistory.length})</span>
            </button>
          )}
        </div>`;

content = content.replace(targetHeader, newHeader);

// 4. Update the Upcoming tab button label
content = content.replace(
  'Upcoming Schedules ({upcomingRunsList.length})',
  'Schedules & Next Runs ({allSchedules.length})'
);

// 5. Update Tab Content for Upcoming Schedules:
// Separate Configured Schedules (with Delete buttons) from Forecast Cycles (read-only forecast preview)
const oldUpcomingTab = `      {/* TAB CONTENT: UPCOMING SCHEDULES */}
      {activeTab === 'upcoming' && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-2.5 px-3">Cycle</th>
                <th className="py-2.5 px-3">Exact Scheduled Time</th>
                <th className="py-2.5 px-3">Strategy Profile</th>
                <th className="py-2.5 px-3">Cadence</th>
                <th className="py-2.5 px-3">Notification Email</th>
                <th className="py-2.5 px-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {upcomingRunsList.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-slate-400">
                    No upcoming runs scheduled. Configure your strategy profile above and click <strong>+ Save New Schedule</strong>.
                  </td>
                </tr>
              ) : (
                upcomingRunsList.map((item, idx) => {
                  const d = new Date(item.datetime || item);
                  const formatted = !isNaN(d.getTime())
                    ? d.toLocaleString('en-IN', {
                        weekday: 'short',
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: true,
                      }) + ' IST'
                    : String(item.datetime);

                  return (
                    <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-3 px-3 font-semibold text-slate-700">
                        {idx === 0 ? (
                          <span className="inline-flex items-center gap-1.5 text-emerald-700 font-bold">
                            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                            <span>Next Run</span>
                          </span>
                        ) : (
                          <span className="text-slate-500">+{idx} Cycle</span>
                        )}
                      </td>
                      <td className="py-3 px-3 font-mono font-medium text-slate-800">{formatted}</td>
                      <td className="py-3 px-3 text-slate-700">
                        {item.profile_name || scheduleConfig?.profile || 'Global Quality Growth Core'}
                      </td>
                      <td className="py-3 px-3 text-slate-600">
                        <span className="font-semibold text-slate-800 block">
                          {item.frequency || scheduleConfig?.frequency || 'Daily'} @ {item.time_of_day || scheduleConfig?.time || '08:30'}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono block">
                          {item.schedule_id || 'scheduled'}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        {(() => {
                          const emails = item.notification_email || scheduleConfig?.notifyEmail || '';
                          const list = emails.split(/[,;]+/).map((e) => e.trim()).filter(Boolean);
                          if (list.length === 0) {
                            return <span className="text-[11px] text-slate-400 italic font-mono">Default Institutional</span>;
                          }
                          return (
                            <div className="flex flex-wrap gap-1 max-w-[260px]">
                              {list.map((em, eIdx) => (
                                <span
                                  key={eIdx}
                                  className="inline-flex items-center gap-1 font-mono text-[10px] text-slate-800 bg-slate-50 border border-slate-200 px-1.5 py-0.5 rounded shadow-2xs"
                                  title={\`Configured: \${em}\`}
                                >
                                  <span>✉️</span>
                                  <span className="font-semibold text-slate-700">{em}</span>
                                </span>
                              ))}
                            </div>
                          );
                        })()}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <div className="flex items-center justify-end space-x-1.5">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            Armed
                          </span>
                          <button
                            type="button"
                            onClick={() => handleEditUpcomingSchedule(item)}
                            className="px-2 py-0.5 text-[11px] font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded hover:text-[#146b63] transition-colors cursor-pointer"
                            title="Edit this schedule in Configuration card"
                          >
                            ✏️ Edit
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              handleDeleteUpcomingSchedule(
                                item.schedule_id,
                                item.label || \`\${item.frequency} @ \${item.time_of_day}\`
                              )
                            }
                            className="px-2 py-0.5 text-[11px] font-semibold text-rose-600 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded transition-colors cursor-pointer"
                            title="Delete this schedule permanently"
                          >
                            🗑️ Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}`;

const newUpcomingTab = `      {/* TAB CONTENT: ACTIVE SCHEDULES & FORECAST */}
      {activeTab === 'upcoming' && (
        <div className="space-y-6">
          {/* 1. ACTIVE SCHEDULES (Each schedule is an independent entry in DB) */}
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
                    allSchedules.map((s) => {
                      const isCurrentEditing = scheduleConfig?.scheduleId === s.schedule_id;
                      const emails = s.notification_email ? s.notification_email.split(/[,;]+/).map((e) => e.trim()).filter(Boolean) : [];

                      return (
                        <tr key={s.schedule_id} className={\`transition-colors \${isCurrentEditing ? 'bg-teal-50/50' : 'hover:bg-slate-50/70'}\`}>
                          <td className="py-3 px-3">
                            <div className="flex items-center space-x-2">
                              <span className="font-bold text-slate-800 text-xs">
                                {s.frequency} @ {s.time_of_day} IST
                              </span>
                              {isCurrentEditing && (
                                <span className="px-1.5 py-0.2 bg-[#146b63] text-white text-[9px] font-bold rounded">
                                  Editing
                                </span>
                              )}
                            </div>
                            <span className="font-mono text-[10px] text-slate-400 block">{s.schedule_id}</span>
                          </td>
                          <td className="py-3 px-3 text-slate-700 font-medium">
                            {s.profile_name || 'Default Strategy'}
                          </td>
                          <td className="py-3 px-3">
                            {emails.length === 0 ? (
                              <span className="text-[11px] text-slate-400 italic">Default Institutional</span>
                            ) : (
                              <div className="flex flex-wrap gap-1 max-w-[260px]">
                                {emails.map((em, eIdx) => (
                                  <span
                                    key={eIdx}
                                    className="inline-flex items-center gap-1 font-mono text-[10px] text-slate-800 bg-slate-50 border border-slate-200 px-1.5 py-0.5 rounded"
                                  >
                                    <span>✉️</span>
                                    <span>{em}</span>
                                  </span>
                                ))}
                              </div>
                            )}
                          </td>
                          <td className="py-3 px-3">
                            <span
                              className={\`px-2 py-0.5 rounded text-[10px] font-semibold \${
                                s.is_enabled
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : 'bg-amber-50 text-amber-700 border border-amber-200'
                              }\`}
                            >
                              {s.is_enabled ? 'Active' : 'Paused'}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-right">
                            <div className="flex items-center justify-end space-x-1.5">
                              <button
                                type="button"
                                onClick={() => handleEditUpcomingSchedule({ schedule_id: s.schedule_id })}
                                className="px-2.5 py-1 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded hover:text-[#146b63] transition-colors cursor-pointer"
                                title="Edit this schedule"
                              >
                                ✏️ Edit
                              </button>
                              <button
                                type="button"
                                onClick={() =>
                                  handleDeleteUpcomingSchedule(
                                    s.schedule_id,
                                    \`\${s.frequency} @ \${s.time_of_day} (\${s.profile_name || 'Strategy'})\`
                                  )
                                }
                                className="px-2.5 py-1 text-xs font-semibold text-rose-600 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded transition-colors cursor-pointer"
                                title="Delete this schedule permanently"
                              >
                                🗑️ Delete Schedule
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* 2. UPCOMING EXECUTION FORECAST (Chronological Preview) */}
          {upcomingRunsList.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <span>📅</span>
                  <span>Execution Cycles Forecast (Next {upcomingRunsList.length} Runs)</span>
                </h3>
                <span className="text-[11px] text-slate-400">
                  Calculated execution timeline based on active schedules.
                </span>
              </div>

              <div className="overflow-x-auto border border-slate-200/80 rounded-md">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                      <th className="py-2.5 px-3">Cycle</th>
                      <th className="py-2.5 px-3">Execution Time</th>
                      <th className="py-2.5 px-3">Strategy Profile</th>
                      <th className="py-2.5 px-3">Associated Schedule</th>
                      <th className="py-2.5 px-3 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {upcomingRunsList.map((item, idx) => {
                      const d = new Date(item.datetime || item);
                      const formatted = !isNaN(d.getTime())
                        ? d.toLocaleString('en-IN', {
                            weekday: 'short',
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                            hour12: true,
                          }) + ' IST'
                        : String(item.datetime);

                      return (
                        <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                          <td className="py-2.5 px-3 font-semibold text-slate-700">
                            {idx === 0 ? (
                              <span className="inline-flex items-center gap-1.5 text-emerald-700 font-bold">
                                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                                <span>Next Run</span>
                              </span>
                            ) : (
                              <span className="text-slate-500">+{idx} Cycle</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 font-mono font-medium text-slate-800">{formatted}</td>
                          <td className="py-2.5 px-3 text-slate-700">
                            {item.profile_name || 'Default Strategy'}
                          </td>
                          <td className="py-2.5 px-3 text-slate-600">
                            <span className="font-semibold text-slate-800 block">
                              {item.frequency || 'Daily'} @ {item.time_of_day || '08:30'}
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono block">
                              {item.schedule_id}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Armed
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}`;

content = content.replace(oldUpcomingTab, newUpcomingTab);

// 6. In Action column of past runs (All Runs / Completed), add the 🗑️ Delete button next to Open
const oldActionCol = `                      <td className="py-3 px-3 text-right">
                        {isRunning ? (
                          <button
                            disabled
                            className="px-3 py-1 bg-slate-100 text-slate-400 border border-slate-200 text-xs font-semibold rounded cursor-not-allowed"
                          >
                            Running...
                          </button>
                        ) : (
                          <button
                            onClick={() => handleOpenRun(item.id)}
                            className={\`px-3 py-1 text-xs font-semibold rounded shadow-2xs transition-colors cursor-pointer \${
                              isSelected
                                ? 'bg-[#146b63] text-white hover:bg-[#0f5750]'
                                : 'bg-white border border-slate-300 hover:bg-slate-50 text-slate-700'
                            }\`}
                          >
                            {isSelected ? 'Current' : 'Open'}
                          </button>
                        )}
                      </td>`;

const newActionCol = `                      <td className="py-3 px-3 text-right">
                        {isRunning ? (
                          <button
                            disabled
                            className="px-3 py-1 bg-slate-100 text-slate-400 border border-slate-200 text-xs font-semibold rounded cursor-not-allowed"
                          >
                            Running...
                          </button>
                        ) : (
                          <div className="flex items-center justify-end space-x-1.5">
                            <button
                              onClick={() => handleOpenRun(item.id)}
                              className={\`px-3 py-1 text-xs font-semibold rounded shadow-2xs transition-colors cursor-pointer \${
                                isSelected
                                  ? 'bg-[#146b63] text-white hover:bg-[#0f5750]'
                                  : 'bg-white border border-slate-300 hover:bg-slate-50 text-slate-700'
                              }\`}
                            >
                              {isSelected ? 'Current' : 'Open'}
                            </button>
                            <button
                              onClick={() => handleDeleteRun(item.id, item.run)}
                              className="px-2 py-1 text-xs font-semibold rounded text-rose-600 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition-colors cursor-pointer"
                              title="Delete this run and its results from the database"
                            >
                              🗑️
                            </button>
                          </div>
                        )}
                      </td>`;

content = content.replace(oldActionCol, newActionCol);

fs.writeFileSync(rhtPath, content.replace(/\n/g, '\r\n'), 'utf8');
console.log('Updated RunHistoryTable.jsx successfully.');

