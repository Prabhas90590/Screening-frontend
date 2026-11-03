const fs = require('fs');
let content = fs.readFileSync('frontend/src/data/mockData.js', 'utf8');
content = content.replace(/\r\n/g, '\n');

const target = `export const INITIAL_SCHEDULE = {
  profile: 'None',
  frequency: 'Weekly',
  activeDays: ['mon'],
  time: '06:00',
  timezone: 'America/New_York',
  refreshDataFirst: true,
  notifyEmail: '',
  notifyTriggers: {
    runCompletes: true,
    runFails: true,
    dataBlockers: true,
  },
};`;

const replacement = `export const INITIAL_SCHEDULE = {
  profile: 'None',
  frequency: 'Daily',
  dailyType: 'trading_days',
  activeDays: ['mon', 'tue', 'wed', 'thu', 'fri'],
  time: '08:30',
  timezone: 'Asia/Kolkata',
  refreshDataFirst: true,
  notifyEmail: '',
  notifyTriggers: {
    runCompletes: true,
    runFails: true,
    dataBlockers: true,
  },
};`;

if (content.includes(target)) {
  content = content.replace(target, replacement);
  fs.writeFileSync('frontend/src/data/mockData.js', content, 'utf8');
  console.log('SUCCESS: Updated INITIAL_SCHEDULE in mockData.js');
} else {
  console.log('ERROR: target not found in mockData.js');
}

