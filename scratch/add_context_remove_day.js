const fs = require('fs');

let p = 'frontend/src/context/ScreeningContext.jsx';
let content = fs.readFileSync(p, 'utf8').replace(/\r\n/g, '\n');

// 1. Add removeScheduleDay to imports
content = content.replace(
  'deleteScheduleConfig,',
  'deleteScheduleConfig,\n  removeScheduleDay,'
);

// 2. Add removeDayFromSchedule after deleteScheduleFromBackend
const targetMethod = `  const deleteScheduleFromBackend = async (schedId) => {`;

const newMethod = `  const removeDayFromSchedule = async (schedId, day) => {
    if (!schedId || !day) return false;
    try {
      const res = await removeScheduleDay(schedId, day);
      if (res) {
        if (res.schedules) setAllSchedules(res.schedules);
        if (res.next_runs) setNextRuns(res.next_runs);
        if (res.next_runs_detailed) setNextRunsDetailed(res.next_runs_detailed);
        if (res.next_runs_by_frequency) setNextRunsByFrequency(res.next_runs_by_frequency);
        if (res.schedule && scheduleConfig?.scheduleId === schedId) {
          setScheduleConfig((prev) => ({
            ...prev,
            activeDays: res.schedule.active_days || [],
            isEnabled: res.schedule.is_enabled,
          }));
        }
        return true;
      }
      return false;
    } catch (err) {
      console.error('[ScreeningContext] Could not remove day from schedule:', err.message);
      return false;
    }
  };

  const deleteScheduleFromBackend = async (schedId) => {`;

content = content.replace(targetMethod, newMethod);

// 3. Expose removeDayFromSchedule in context value
content = content.replace(
  'deleteScheduleFromBackend,\n',
  'deleteScheduleFromBackend,\n        removeDayFromSchedule,\n'
);

fs.writeFileSync(p, content.replace(/\n/g, '\r\n'), 'utf8');
console.log('Updated ScreeningContext.jsx with removeDayFromSchedule');

