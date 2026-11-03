const fs = require('fs');

let ctxPath = 'frontend/src/context/ScreeningContext.jsx';
let content = fs.readFileSync(ctxPath, 'utf8').replace(/\r\n/g, '\n');

// 1. Add deleteScreeningRun and clearScreeningRuns to imports
if (!content.includes('deleteScreeningRun')) {
  content = content.replace(
    'deleteScheduleConfig,\n} from \'../services/api\';',
    'deleteScheduleConfig,\n  deleteScreeningRun,\n  clearScreeningRuns,\n} from \'../services/api\';'
  );
}

// 2. Update saveScheduleToBackend and deleteScheduleFromBackend and add deleteRunFromBackend and clearAllRunsFromBackend
const targetBlock = `  const saveScheduleToBackend = async (updates = {}) => {
    const merged = { ...scheduleConfig, ...updates };
    const cleanTime = (merged.time || '08:30').replace(':', '');
    const cleanFreq = (merged.frequency || 'daily').toLowerCase();
    let schedId = merged.scheduleId;
    if (!schedId) {
      const baseId = \`sched-\${cleanFreq}-\${cleanTime}\`;
      const exists = allSchedules.some((s) => s.schedule_id === baseId);
      schedId = exists ? \`\${baseId}-\${Math.random().toString(36).substring(2, 6)}\` : baseId;
    }

    const payload = {
      schedule_id: schedId,
      profile_id: merged.selectedProfileId || undefined,
      profile_name: merged.profile || 'Default Strategy',
      frequency: merged.frequency || 'Daily',
      daily_type: merged.dailyType || 'trading_days',
      active_days: merged.activeDays || ['mon', 'tue', 'wed', 'thu', 'fri'],
      day_of_month: merged.dayOfMonth || 1,
      time_of_day: merged.time || '08:30',
      timezone: merged.timezone || 'Asia/Kolkata',
      cron_expression: merged.cronExpression || '0 9 * * 1-5',
      is_enabled: merged.isEnabled ?? true,
      auto_run: merged.autoRun ?? true,
      refresh_data_first: merged.refreshDataFirst ?? true,
      skip_holidays: merged.skipHolidays ?? true,
      notify_on_complete: true,
      notification_email: (merged.notifyEmail || '').trim() || null,
      notify_triggers: merged.notifyTriggers || { runCompletes: true, runFails: true, dataBlockers: true },
    };

    try {
      const res = await saveScheduleConfig(payload);
      if (res) {
        if (res.schedules) setAllSchedules(res.schedules);
        if (res.next_runs) setNextRuns(res.next_runs);
        if (res.next_runs_detailed) setNextRunsDetailed(res.next_runs_detailed);
        if (res.next_runs_by_frequency) setNextRunsByFrequency(res.next_runs_by_frequency);
        setScheduleConfig((prev) => ({ ...prev, ...merged, scheduleId: schedId }));
        return res;
      }
    } catch (err) {
      console.warn('[ScreeningContext] Could not save schedule to backend:', err.message);
      setScheduleConfig((prev) => ({ ...prev, ...merged, scheduleId: schedId }));
    }
  };

  const deleteScheduleFromBackend = async (schedId) => {
    if (!schedId || schedId === 'default') {
      return false;
    }
    try {
      const res = await deleteScheduleConfig(schedId);
      if (res) {
        if (res.schedules) setAllSchedules(res.schedules);
        if (res.next_runs) setNextRuns(res.next_runs);
        if (res.next_runs_detailed) setNextRunsDetailed(res.next_runs_detailed);
        if (res.next_runs_by_frequency) setNextRunsByFrequency(res.next_runs_by_frequency);
        if (res.schedules && res.schedules.length === 0) {
          setAllSchedules([]);
          setNextRuns([]);
          setNextRunsDetailed([]);
          setNextRunsByFrequency({ Daily: [], Weekly: [], Monthly: [], Custom: [] });
          setScheduleConfig((prev) => ({
            ...prev,
            scheduleId: '',
            time: '08:30',
            frequency: 'Daily',
          }));
        } else if (res.schedule) {
          const s = res.schedule;
          setScheduleConfig({
            scheduleId: s.schedule_id,
            profile: s.profile_name,
            selectedProfileId: s.profile_id,
            frequency: s.frequency,
            dailyType: s.daily_type || 'trading_days',
            activeDays: s.active_days || ['mon', 'tue', 'wed', 'thu', 'fri'],
            dayOfMonth: s.day_of_month || 1,
            time: s.time_of_day || '08:30',
            timezone: s.timezone || 'Asia/Kolkata',
            cronExpression: s.cron_expression || '0 9 * * 1-5',
            refreshDataFirst: s.refresh_data_first ?? true,
            skipHolidays: s.skip_holidays ?? true,
            notifyEmail: s.notification_email || '',
            notifyTriggers: s.notify_triggers,
            isEnabled: s.is_enabled ?? true,
          });
        }
        return true;
      }
      return false;
    } catch (err) {
      console.error('[ScreeningContext] Could not delete schedule:', err.message);
      return false;
    }
  };`;

const replacementBlock = `  const saveScheduleToBackend = async (updates = {}, forceNew = false) => {
    const merged = { ...scheduleConfig, ...updates };
    const cleanTime = (merged.time || '08:30').replace(':', '');
    const cleanFreq = (merged.frequency || 'daily').toLowerCase();
    let schedId = forceNew ? '' : merged.scheduleId;
    if (!schedId) {
      const rand = Math.random().toString(36).substring(2, 7);
      schedId = \`sched-\${cleanFreq}-\${cleanTime}-\${rand}\`;
    }

    const payload = {
      schedule_id: schedId,
      profile_id: merged.selectedProfileId || undefined,
      profile_name: merged.profile || 'Default Strategy',
      frequency: merged.frequency || 'Daily',
      daily_type: merged.dailyType || 'trading_days',
      active_days: merged.activeDays || ['mon', 'tue', 'wed', 'thu', 'fri'],
      day_of_month: merged.dayOfMonth || 1,
      time_of_day: merged.time || '08:30',
      timezone: merged.timezone || 'Asia/Kolkata',
      cron_expression: merged.cronExpression || '0 9 * * 1-5',
      is_enabled: merged.isEnabled ?? true,
      auto_run: merged.autoRun ?? true,
      refresh_data_first: merged.refreshDataFirst ?? true,
      skip_holidays: merged.skipHolidays ?? true,
      notify_on_complete: true,
      notification_email: (merged.notifyEmail || '').trim() || null,
      notify_triggers: merged.notifyTriggers || { runCompletes: true, runFails: true, dataBlockers: true },
    };

    try {
      const res = await saveScheduleConfig(payload);
      if (res) {
        if (res.schedules) setAllSchedules(res.schedules);
        if (res.next_runs) setNextRuns(res.next_runs);
        if (res.next_runs_detailed) setNextRunsDetailed(res.next_runs_detailed);
        if (res.next_runs_by_frequency) setNextRunsByFrequency(res.next_runs_by_frequency);
        setScheduleConfig((prev) => ({ ...prev, ...merged, scheduleId: schedId }));
        return res;
      }
    } catch (err) {
      console.warn('[ScreeningContext] Could not save schedule to backend:', err.message);
      setScheduleConfig((prev) => ({ ...prev, ...merged, scheduleId: schedId }));
    }
  };

  const deleteScheduleFromBackend = async (schedId) => {
    if (!schedId || schedId === 'default' || schedId === 'default-schedule') {
      return false;
    }
    try {
      const res = await deleteScheduleConfig(schedId);
      if (res) {
        const remaining = res.schedules || [];
        setAllSchedules(remaining);
        setNextRuns(res.next_runs || []);
        setNextRunsDetailed(res.next_runs_detailed || []);
        setNextRunsByFrequency(res.next_runs_by_frequency || { Daily: [], Weekly: [], Monthly: [], Custom: [] });

        if (remaining.length === 0) {
          setScheduleConfig((prev) => ({
            ...prev,
            scheduleId: '',
            time: '08:30',
            frequency: 'Daily',
          }));
        } else {
          // If the schedule we just deleted was the currently active/editing one, switch to the first remaining schedule
          const isDeletedCurrent = scheduleConfig?.scheduleId === schedId;
          const target = isDeletedCurrent ? remaining[0] : (remaining.find((s) => s.schedule_id === scheduleConfig?.scheduleId) || remaining[0]);
          if (target) {
            setScheduleConfig({
              scheduleId: target.schedule_id,
              profile: target.profile_name,
              selectedProfileId: target.profile_id,
              frequency: target.frequency,
              dailyType: target.daily_type || 'trading_days',
              activeDays: target.active_days || ['mon', 'tue', 'wed', 'thu', 'fri'],
              dayOfMonth: target.day_of_month || 1,
              time: target.time_of_day || '08:30',
              timezone: target.timezone || 'Asia/Kolkata',
              cronExpression: target.cron_expression || '0 9 * * 1-5',
              refreshDataFirst: target.refresh_data_first ?? true,
              skipHolidays: target.skip_holidays ?? true,
              notifyEmail: target.notification_email || '',
              notifyTriggers: target.notify_triggers,
              isEnabled: target.is_enabled ?? true,
            });
          }
        }
        return true;
      }
      return false;
    } catch (err) {
      console.error('[ScreeningContext] Could not delete schedule:', err.message);
      return false;
    }
  };

  const deleteRunFromBackend = async (runId) => {
    if (!runId) return false;
    try {
      await deleteScreeningRun(runId);
      setRunHistory((prev) => prev.filter((r) => r.id !== runId && r.run !== runId));
      setSelectedRunId((prev) => (prev === runId ? null : prev));
      return true;
    } catch (err) {
      console.error('[ScreeningContext] Failed to delete run from backend:', err.message);
      return false;
    }
  };

  const clearAllRunsFromBackend = async () => {
    try {
      await clearScreeningRuns();
      setRunHistory([]);
      setSelectedRunId(null);
      setSecurities([]);
      return true;
    } catch (err) {
      console.error('[ScreeningContext] Failed to clear all runs from backend:', err.message);
      return false;
    }
  };`;

if (content.includes(targetBlock)) {
  content = content.replace(targetBlock, replacementBlock);
  console.log('Replaced schedule methods & added run deletion methods in context.');
} else {
  console.error('targetBlock not matched in context');
}

// 3. Add deleteRunFromBackend and clearAllRunsFromBackend to context Provider value
content = content.replace(
  'deleteScheduleFromBackend,\n',
  'deleteScheduleFromBackend,\n        deleteRunFromBackend,\n        clearAllRunsFromBackend,\n'
);

fs.writeFileSync(ctxPath, content.replace(/\n/g, '\r\n'), 'utf8');
console.log('Updated ScreeningContext.jsx successfully.');

