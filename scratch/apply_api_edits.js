const fs = require('fs');
let p = 'frontend/src/services/api.js';
let content = fs.readFileSync(p, 'utf8');

const runEndpoints = `

/**
 * Permanently delete a screening run and its results from backend.
 */
export async function deleteScreeningRun(runId) {
  try {
    const res = await fetch(\`\${API_BASE}/screenings/\${encodeURIComponent(runId)}\`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || \`HTTP \${res.status}: Failed to delete screening run\`);
    }
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to delete screening run:', err.message);
    throw err;
  }
}

/**
 * Permanently delete ALL screening runs and their results from backend.
 */
export async function clearScreeningRuns() {
  try {
    const res = await fetch(\`\${API_BASE}/screenings\`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || \`HTTP \${res.status}: Failed to clear screening runs\`);
    }
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to clear screening runs:', err.message);
    throw err;
  }
}
`;

content += runEndpoints;
fs.writeFileSync(p, content, 'utf8');
console.log('Appended deleteScreeningRun and clearScreeningRuns to api.js');

