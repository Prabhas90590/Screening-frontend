const fs = require('fs');

let p = 'frontend/src/components/schedule/RunHistoryTable.jsx';
let content = fs.readFileSync(p, 'utf8').replace(/\r\n/g, '\n');

// 1. Remove premature displayedForecastRuns at line 125
const prematureDeclaration = `  const displayedSchedules = cadenceFilter === 'all'
    ? (allSchedules || [])
    : (allSchedules || []).filter((s) => (s.frequency || '').toLowerCase() === cadenceFilter);

  const displayedForecastRuns = cadenceFilter === 'all'
    ? upcomingRunsList
    : upcomingRunsList.filter((item) => (item.frequency || '').toLowerCase() === cadenceFilter);`;

const cleanDeclaration = `  const displayedSchedules = cadenceFilter === 'all'
    ? (allSchedules || [])
    : (allSchedules || []).filter((s) => (s.frequency || '').toLowerCase() === cadenceFilter);`;

content = content.replace(prematureDeclaration, cleanDeclaration);

// 2. Put displayedForecastRuns right after upcomingRunsList initialization
const targetUpcomingBlock = `  // Upcoming runs: strictly from saved schedules (no fake fallbacks)
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
                label: \`\${allSchedules[0]?.frequency || 'Daily'} @ \${allSchedules[0]?.time_of_day || '08:30'}\`,
                notification_email: allSchedules[0]?.notification_email || '',
                timezone: allSchedules[0]?.timezone || 'Asia/Kolkata',
              }))
            : []))
    : [];`;

const updatedUpcomingBlock = `  // Upcoming runs: strictly from saved schedules (no fake fallbacks)
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
                label: \`\${allSchedules[0]?.frequency || 'Daily'} @ \${allSchedules[0]?.time_of_day || '08:30'}\`,
                notification_email: allSchedules[0]?.notification_email || '',
                timezone: allSchedules[0]?.timezone || 'Asia/Kolkata',
              }))
            : []))
    : [];

  const displayedForecastRuns = cadenceFilter === 'all'
    ? upcomingRunsList
    : upcomingRunsList.filter((item) => (item.frequency || '').toLowerCase() === cadenceFilter);`;

content = content.replace(targetUpcomingBlock, updatedUpcomingBlock);

fs.writeFileSync(p, content.replace(/\n/g, '\r\n'), 'utf8');
console.log('Fixed ReferenceError in RunHistoryTable.jsx');

