import React, { useState, useEffect } from 'react';
import { useScreening } from '../../context/ScreeningContext';
import { Badge } from '../common/Badge';

// Helper to compute exact upcoming schedule dates
function computeUpcomingDates(config, count = 3) {
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
      const dayOfWeek = cand.getDay();

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

export const RunHistoryTable = () => {
  const {
    runHistory,
    setActiveNav,
    setSelectedRunId,
    loadRunHistory,
    selectedRunId,
    isScreeningRunning,
    scheduleConfig,
    nextRuns,
    triggerRunNow,
    profiles,
    setResultsTab,
  } = useScreening();

  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'completed' | 'current' | 'upcoming'

  // Auto-refresh every 10 seconds to promptly capture background scheduled executions
  useEffect(() => {
    if (loadRunHistory) {
      loadRunHistory();
      const interval = setInterval(() => {
        loadRunHistory();
      }, 10000);
      return () => clearInterval(interval);
    }
  }, []);

  const getStatusBadge = (status) => {
    switch (status) {
      case 'Running':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-600 animate-pulse"></span>
            <span>Running</span>
          </span>
        );
      case 'Succeeded':
        return <Badge variant="teal">Succeeded</Badge>;
      case 'Warnings':
        return <Badge variant="amber">Warnings</Badge>;
      case 'Failed':
      case 'Failed (provider)':
        return <Badge variant="red">Failed</Badge>;
      default:
        return <Badge variant="gray">{status}</Badge>;
    }
  };

  const getTriggerBadge = (triggerType) => {
    const isScheduled = (triggerType || '').toLowerCase() === 'scheduled';
    if (isScheduled) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200">
          <span>⏰</span>
          <span>Scheduled</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-sky-50 text-sky-700 border border-sky-200">
        <span>⚡</span>
        <span>Instant</span>
      </span>
    );
  };

  const handleOpenRun = (runId) => {
    if (setSelectedRunId) {
      setSelectedRunId(runId);
    }
    if (setResultsTab) {
      setResultsTab('top20');
    }
    setActiveNav('results');
  };

  // Filter subsets
  const completedRuns = runHistory.filter((r) => r.status === 'Succeeded' || r.status === 'Warnings');
  const runningRuns = runHistory.filter((r) => r.status === 'Running');

  // Exact upcoming date calculations
  let dateObjects = [];
  if (nextRuns && nextRuns.length > 0) {
    dateObjects = nextRuns.map((r) => new Date(r)).filter((d) => !isNaN(d.getTime()));
  }
  if (dateObjects.length === 0) {
    dateObjects = computeUpcomingDates(scheduleConfig, 3);
  }

  // Selected profile for info display
  const targetProfile =
    profiles?.find((p) => p.id === scheduleConfig?.selectedProfileId) ||
    profiles?.find((p) => scheduleConfig?.profile === `${p.name} - Version ${p.versionNumber}`) ||
    (profiles && profiles.length > 0 ? profiles[0] : null);

  const displayRuns = activeTab === 'completed' ? completedRuns : runHistory;

  return (
    <div className="bg-white rounded-lg border border-slate-200/80 p-6 shadow-2xs space-y-4">
      {/* Header & Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-3">
          <h2 className="text-base font-bold text-slate-800">Screening Executions</h2>
          <span className="text-xs text-slate-400 font-normal">| Live Run History & Schedules</span>
        </div>

        {/* Multi-Tab Navigation */}
        <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-md text-xs font-medium">
          <button
            type="button"
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1 rounded transition-colors cursor-pointer ${
              activeTab === 'all'
                ? 'bg-white text-slate-800 font-bold shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            All Runs ({runHistory.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('completed')}
            className={`px-3 py-1 rounded transition-colors cursor-pointer ${
              activeTab === 'completed'
                ? 'bg-white text-slate-800 font-bold shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Completed ({completedRuns.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('current')}
            className={`px-3 py-1 rounded flex items-center space-x-1.5 transition-colors cursor-pointer ${
              activeTab === 'current'
                ? 'bg-white text-slate-800 font-bold shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {runningRuns.length > 0 || isScreeningRunning ? (
              <span className="h-2 w-2 rounded-full bg-blue-500 animate-ping" />
            ) : null}
            <span>Active Run ({runningRuns.length > 0 ? runningRuns.length : 'Idle'})</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('upcoming')}
            className={`px-3 py-1 rounded transition-colors cursor-pointer ${
              activeTab === 'upcoming'
                ? 'bg-white text-slate-800 font-bold shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Upcoming Schedules ({dateObjects.length})
          </button>
        </div>

        <button
          type="button"
          onClick={loadRunHistory}
          className="flex items-center space-x-1.5 px-2.5 py-1 bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200 text-xs font-semibold rounded shadow-2xs transition-colors cursor-pointer self-start sm:self-auto"
          title="Reload historical runs from database"
        >
          <span>↻</span>
          <span>Refresh</span>
        </button>
      </div>

      {/* TAB CONTENT: ACTIVE / CURRENT RUN */}
      {activeTab === 'current' && (
        <div className="py-2">
          {runningRuns.length > 0 || isScreeningRunning ? (
            <div className="p-5 rounded-lg border border-blue-200 bg-blue-50/40 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="relative flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
                  </span>
                  <span className="font-bold text-sm text-blue-900">Execution In Progress</span>
                  {runningRuns[0]?.trigger_type && getTriggerBadge(runningRuns[0].trigger_type)}
                </div>
                <span className="font-mono text-xs text-blue-700 bg-blue-100/60 px-2.5 py-0.5 rounded">
                  {runningRuns[0]?.id || 'Evaluating pipeline'}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 text-xs">
                <div className="bg-white p-3 rounded border border-blue-100">
                  <span className="text-slate-500">Strategy Profile:</span>
                  <p className="font-semibold text-slate-800 mt-0.5">
                    {runningRuns[0]?.rules || scheduleConfig?.profile || 'Institutional Quality Growth'}
                  </p>
                </div>
                <div className="bg-white p-3 rounded border border-blue-100">
                  <span className="text-slate-500">Current Phase:</span>
                  <p className="font-semibold text-blue-700 mt-0.5 flex items-center space-x-1.5">
                    <svg className="animate-spin h-3.5 w-3.5 text-blue-600" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Evaluating fundamental rules & rankings...</span>
                  </p>
                </div>
                <div className="bg-white p-3 rounded border border-blue-100">
                  <span className="text-slate-500">Execution Mode:</span>
                  <p className="font-semibold text-slate-800 mt-0.5">
                    {(runningRuns[0]?.trigger_type || 'instant').toUpperCase()} EXECUTION
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 rounded-lg border border-slate-200 bg-slate-50/50 flex flex-col items-center justify-center text-center space-y-3">
              <div className="h-10 w-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-lg">
                ✓
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-800">No Run Currently In Progress</h3>
                <p className="text-xs text-slate-500 max-w-md mt-1">
                  The automated scheduler background daemon is live and checking every 10 seconds. When your scheduled
                  time triggers, the run will execute automatically and appear here.
                </p>
              </div>
              <div className="flex items-center space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setActiveTab('upcoming')}
                  className="px-3 py-1.5 bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 text-xs font-semibold rounded shadow-2xs transition-colors cursor-pointer"
                >
                  View Next Schedule
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (targetProfile && triggerRunNow) {
                      triggerRunNow(targetProfile.id, scheduleConfig?.notifyEmail);
                      setActiveTab('current');
                    }
                  }}
                  className="px-3 py-1.5 bg-[#146b63] hover:bg-[#0f5750] text-white text-xs font-semibold rounded shadow-2xs transition-colors cursor-pointer"
                >
                  Trigger Instant Run Now
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: UPCOMING SCHEDULES */}
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
              {dateObjects.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-slate-400">
                    No upcoming runs scheduled. Verify the schedule is enabled and configured above.
                  </td>
                </tr>
              ) : (
                dateObjects.map((d, idx) => {
                  const formatted =
                    d.toLocaleString('en-IN', {
                      weekday: 'short',
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                      hour12: true,
                    }) + ' IST';

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
                        {scheduleConfig?.profile || 'Global Quality Growth Core'}
                      </td>
                      <td className="py-3 px-3 text-slate-600">
                        {scheduleConfig?.frequency || 'Daily'} (
                        {scheduleConfig?.dailyType === 'trading_days' ? 'Trading Days' : 'Calendar Days'})
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-600">
                        {scheduleConfig?.notifyEmail || 'Default Institutional Distribution'}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Armed & Queued
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB CONTENT: ALL RUNS & COMPLETED RUNS */}
      {(activeTab === 'all' || activeTab === 'completed') && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-2.5 px-3">Run</th>
                <th className="py-2.5 px-3">Type</th>
                <th className="py-2.5 px-3">Started</th>
                <th className="py-2.5 px-3">Rules / Strategy</th>
                <th className="py-2.5 px-3">Screened</th>
                <th className="py-2.5 px-3">Selected</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Duration</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {displayRuns.length === 0 ? (
                <tr>
                  <td colSpan="9" className="py-8 text-center text-slate-400">
                    {activeTab === 'completed'
                      ? 'No completed screening executions recorded yet.'
                      : 'No screening executions recorded yet. Select a profile above and click "Run now" or wait for scheduled execution.'}
                  </td>
                </tr>
              ) : (
                displayRuns.map((item) => {
                  const isSelected = item.id === selectedRunId;
                  const isRunning = item.status === 'Running';

                  return (
                    <tr
                      key={item.id}
                      className={`transition-colors ${
                        isSelected ? 'bg-teal-50/40 hover:bg-teal-50/60' : 'hover:bg-slate-50/70'
                      }`}
                    >
                      <td className="py-3 px-3 font-mono font-medium text-slate-800">
                        <div className="flex items-center space-x-1.5">
                          <span className="truncate max-w-[170px]" title={item.run}>
                            {item.run}
                          </span>
                          {isSelected && !isRunning && (
                            <span className="px-1.5 py-0.2 bg-teal-100 text-teal-800 rounded text-[9px] font-semibold">
                              Viewing
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-3">{getTriggerBadge(item.trigger_type)}</td>
                      <td className="py-3 px-3 font-mono text-slate-600">{item.started}</td>
                      <td className="py-3 px-3 text-slate-600">
                        <span className="truncate max-w-[180px] block" title={item.rules}>
                          {item.rules}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-700">
                        {isRunning ? (
                          <span className="flex items-center space-x-1 text-blue-600 font-semibold">
                            <svg className="animate-spin h-3 w-3 text-blue-600" viewBox="0 0 24 24" fill="none">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <span>Evaluating...</span>
                          </span>
                        ) : typeof item.screened === 'number' ? (
                          item.screened.toLocaleString()
                        ) : (
                          item.screened
                        )}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-700">
                        {isRunning ? (
                          <span className="text-slate-400">—</span>
                        ) : (
                          <span className="font-bold text-teal-700">{item.selected}</span>
                        )}
                      </td>
                      <td className="py-3 px-3">{getStatusBadge(item.status)}</td>
                      <td className="py-3 px-3 font-mono text-slate-600">{item.duration}</td>
                      <td className="py-3 px-3 text-right">
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
                            className={`px-3 py-1 text-xs font-semibold rounded shadow-2xs transition-colors cursor-pointer ${
                              isSelected
                                ? 'bg-[#146b63] text-white hover:bg-[#0f5750]'
                                : 'bg-white border border-slate-300 hover:bg-slate-50 text-slate-700'
                            }`}
                          >
                            {isSelected ? 'Current' : 'Open'}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
