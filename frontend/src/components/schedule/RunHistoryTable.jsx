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
    nextRunsDetailed = [],
    allSchedules = [],
    updateScheduleConfig,
    deleteScheduleFromBackend,
    deleteRunFromBackend,
    clearAllRunsFromBackend,
    removeDayFromSchedule,
    triggerRunNow,
    profiles,
    setResultsTab,
  } = useScreening();

  const handleEditUpcomingSchedule = (item) => {
    const sched = allSchedules.find((s) => s.schedule_id === item.schedule_id);
    if (sched) {
      updateScheduleConfig({
        scheduleId: sched.schedule_id,
        profile: sched.profile_name,
        selectedProfileId: sched.profile_id,
        frequency: sched.frequency,
        dailyType: sched.daily_type || 'trading_days',
        activeDays: sched.active_days || ['mon', 'tue', 'wed', 'thu', 'fri'],
        dayOfMonth: sched.day_of_month || 1,
        time: sched.time_of_day || '08:30',
        timezone: sched.timezone || 'Asia/Kolkata',
        cronExpression: sched.cron_expression || '0 9 * * 1-5',
        refreshDataFirst: sched.refresh_data_first ?? true,
        skipHolidays: sched.skip_holidays ?? true,
        notifyEmail: sched.notification_email || '',
        notifyTriggers: sched.notify_triggers,
        isEnabled: sched.is_enabled ?? true,
      });
    } else {
      updateScheduleConfig({
        scheduleId: item.schedule_id,
        frequency: item.frequency || 'Daily',
        time: item.time_of_day || '08:30',
        profile: item.profile_name || 'Strategy',
        notifyEmail: item.notification_email || '',
      });
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDeleteUpcomingSchedule = async (scheduleId, label) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete the schedule "${label}"?\n\nThis will remove it and cancel all future automated runs.`
    );
    if (confirmed && deleteScheduleFromBackend) {
      await deleteScheduleFromBackend(scheduleId);
    }
  };

  const [cadenceFilter, setCadenceFilter] = useState('all'); // 'all' | 'daily' | 'weekly' | 'monthly' | 'custom'

  const dailySchedules = (allSchedules || []).filter((s) => (s.frequency || '').toLowerCase() === 'daily');
  const weeklySchedules = (allSchedules || []).filter((s) => (s.frequency || '').toLowerCase() === 'weekly');
  const monthlySchedules = (allSchedules || []).filter((s) => (s.frequency || '').toLowerCase() === 'monthly');
  const customSchedules = (allSchedules || []).filter((s) => (s.frequency || '').toLowerCase() === 'custom');

  const displayedSchedules = cadenceFilter === 'all'
    ? (allSchedules || [])
    : (allSchedules || []).filter((s) => (s.frequency || '').toLowerCase() === cadenceFilter);

  const handleDeleteForecastDay = async (schedId, dayKey, dayLabel, freq) => {
    const confirmed = window.confirm(
      `Delete ${dayLabel} from this ${freq || 'Daily'} schedule?\n\nThis will remove ${dayLabel} from the schedule's active days. The schedule will continue running on all other days without deleting the whole schedule.`
    );
    if (confirmed && removeDayFromSchedule) {
      await removeDayFromSchedule(schedId, dayKey);
    }
  };

  const handleDeleteRun = async (runId, runLabel) => {
    const confirmed = window.confirm(
      `Are you sure you want to permanently delete run "${runLabel || runId}" from the database?\n\nThis will delete the execution record, its screened securities, and funnel metrics.`
    );
    if (confirmed && deleteRunFromBackend) {
      await deleteRunFromBackend(runId);
    }
  };

  const handleClearAllRuns = async () => {
    const confirmed = window.confirm(
      `Are you sure you want to delete ALL ${runHistory.length} screening runs from the database?\n\nThis will permanently purge your run history and cannot be undone.`
    );
    if (confirmed && clearAllRunsFromBackend) {
      await clearAllRunsFromBackend();
    }
  };

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

  // Upcoming runs: strictly from saved schedules (no fake fallbacks)
  const upcomingRunsList = (allSchedules && allSchedules.length > 0)
    ? (nextRunsDetailed && nextRunsDetailed.length > 0
        ? nextRunsDetailed
        : (nextRuns && nextRuns.length > 0
            ? nextRuns.map((r) => ({
                datetime: r,
                schedule_id: allSchedules[0]?.schedule_id,
                frequency: allSchedules[0]?.frequency || 'Daily',
                time_of_day: allSchedules[0]?.time_of_day || '08:30',
                profile_name: allSchedules[0]?.profile_name || 'Strategy',
                label: `${allSchedules[0]?.frequency || 'Daily'} @ ${allSchedules[0]?.time_of_day || '08:30'}`,
                notification_email: allSchedules[0]?.notification_email || '',
                timezone: allSchedules[0]?.timezone || 'Asia/Kolkata',
              }))
            : []))
    : [];

  const displayedForecastRuns = cadenceFilter === 'all'
    ? upcomingRunsList
    : upcomingRunsList.filter((item) => (item.frequency || '').toLowerCase() === cadenceFilter);

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
            Schedules & Next Runs ({allSchedules.length})
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

      {/* TAB CONTENT: ACTIVE SCHEDULES & FORECAST */}
      {activeTab === 'upcoming' && (
        <div className="space-y-6">
          {/* 1. ACTIVE SCHEDULES (Each schedule is an independent entry in DB) */}
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
                    className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                      cadenceFilter === tab.id
                        ? 'bg-white text-slate-900 shadow-2xs font-bold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
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
                        No ${cadenceFilter === 'all' ? '' : cadenceFilter} schedules configured. Configure your settings above and click <strong>+ Save New Schedule</strong>.
                      </td>
                    </tr>
                  ) : (
                    displayedSchedules.map((s) => {
                      const isCurrentEditing = scheduleConfig?.scheduleId === s.schedule_id;
                      const emails = s.notification_email ? s.notification_email.split(/[,;]+/).map((e) => e.trim()).filter(Boolean) : [];

                      return (
                        <tr key={s.schedule_id} className={`transition-colors ${isCurrentEditing ? 'bg-teal-50/50' : 'hover:bg-slate-50/70'}`}>
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
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                s.is_enabled
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : 'bg-amber-50 text-amber-700 border border-amber-200'
                              }`}
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
                                    `${s.frequency} @ ${s.time_of_day} (${s.profile_name || 'Strategy'})`
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
          {displayedForecastRuns.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <span>📅</span>
                  <span>Execution Cycles Forecast (Next {displayedForecastRuns.length} Runs)</span>
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
                    {displayedForecastRuns.map((item, idx) => {
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
                                      title={`Delete ${dayShort} from this schedule (remaining days continue running)`}
                                    >
                                      🗑️ Delete {dayShort}
                                    </button>
                                  )}
                                </div>
                              );
                            })()}
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
                {activeTab === 'completed' && <th className="py-2.5 px-3">Report & Notification Delivery</th>}
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
                  <td colSpan={activeTab === 'completed' ? 10 : 9} className="py-8 text-center text-slate-400">
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
                      {activeTab === 'completed' && (
                        <td className="py-3 px-3">
                          {(() => {
                            const rawEmails = item.notification_email || '';
                            const emailList = rawEmails.split(/[,;]+/).map((e) => e.trim()).filter(Boolean);
                            if (emailList.length === 0) {
                              return <span className="text-[11px] text-slate-400 italic">No recipient specified</span>;
                            }
                            return (
                              <div className="space-y-1">
                                <div className="flex flex-wrap gap-1 max-w-[280px]">
                                  {emailList.map((em, eIdx) => (
                                    <span
                                      key={eIdx}
                                      className="inline-flex items-center gap-1 font-mono text-[10px] text-slate-800 bg-slate-50 border border-slate-200 px-1.5 py-0.5 rounded shadow-2xs"
                                      title={`Delivered to: ${em}`}
                                    >
                                      <span>✉️</span>
                                      <span className="font-semibold text-slate-700">{em}</span>
                                    </span>
                                  ))}
                                </div>
                                <span className="text-[10px] text-emerald-700 font-semibold flex items-center gap-1">
                                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-600"></span>
                                  <span>Report Dispatched ({emailList.length} recipient{emailList.length > 1 ? 's' : ''})</span>
                                </span>
                              </div>
                            );
                          })()}
                        </td>
                      )}
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
                          <div className="flex items-center justify-end space-x-1.5">
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
                            <button
                              onClick={() => handleDeleteRun(item.id, item.run)}
                              className="px-2 py-1 text-xs font-semibold rounded text-rose-600 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition-colors cursor-pointer"
                              title="Delete this run and its results from the database"
                            >
                              🗑️
                            </button>
                          </div>
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
