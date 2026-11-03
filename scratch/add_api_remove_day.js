const fs = require('fs');
let p = 'frontend/src/services/api.js';
let content = fs.readFileSync(p, 'utf8');

const fn = `
/**
 * Remove a specific day (e.g. 'wed') from a schedule's active days.
 */
export async function removeScheduleDay(scheduleId, day) {
  try {
    const res = await fetch(\`\${API_BASE}/schedules/\${encodeURIComponent(scheduleId)}/days/\${encodeURIComponent(day)}\`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || \`HTTP \${res.status}: Failed to remove day\`);
    }
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to remove day from schedule:', err.message);
    throw err;
  }
}
`;

content += fn;
fs.writeFileSync(p, content, 'utf8');
console.log('Added removeScheduleDay to api.js');

