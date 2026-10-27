/**
 * API service for communicating with the FastAPI screening backend.
 */

const API_BASE = '/api';

/**
 * Fetch the canonical catalog of all 16 screening metrics and their limits.
 */
export async function fetchRuleCatalog() {
  try {
    const res = await fetch(`${API_BASE}/rules/catalog`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch rule catalog`);
    return await res.json();
  } catch (err) {
    console.warn('[API] Could not fetch rule catalog from backend:', err.message);
    return null;
  }
}

/**
 * Fetch all saved rule profiles from PostgreSQL.
 */
export async function fetchProfiles() {
  try {
    const res = await fetch(`${API_BASE}/rules/profiles`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch profiles`);
    return await res.json();
  } catch (err) {
    console.warn('[API] Could not fetch profiles from backend:', err.message);
    return null;
  }
}

/**
 * Save a new rule profile to PostgreSQL.
 */
export async function createProfile(profileData) {
  try {
    const res = await fetch(`${API_BASE}/rules/profiles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profileData),
    });
    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`HTTP ${res.status}: ${errorText}`);
    }
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to save profile to backend:', err.message);
    throw err;
  }
}

/**
 * Update an existing rule profile in PostgreSQL.
 */
export async function updateProfile(versionId, updateData) {
  try {
    const res = await fetch(`${API_BASE}/rules/profiles/${encodeURIComponent(versionId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updateData),
    });
    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`HTTP ${res.status}: ${errorText}`);
    }
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to update profile in backend:', err.message);
    throw err;
  }
}

/**
 * Activate a rule profile as the primary active strategy in PostgreSQL.
 */
export async function activateProfile(versionId) {
  try {
    const res = await fetch(`${API_BASE}/rules/profiles/${encodeURIComponent(versionId)}/activate`, {
      method: 'PUT',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to activate profile`);
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to activate profile in backend:', err.message);
    throw err;
  }
}

/**
 * Delete a profile from PostgreSQL.
 */
export async function deleteProfile(versionId) {
  try {
    const res = await fetch(`${API_BASE}/rules/profiles/${encodeURIComponent(versionId)}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to delete profile`);
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to delete profile in backend:', err.message);
    throw err;
  }
}

/**
 * Trigger a screening run in the backend.
 */
export async function initiateScreening(payload) {
  try {
    const res = await fetch(`${API_BASE}/screenings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errorData.detail || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to initiate screening:', err.message);
    throw err;
  }
}

/**
 * Fetch historical screening runs ordered by started_at DESC from PostgreSQL.
 */
export async function fetchScreeningRuns(limit = 50) {
  try {
    const res = await fetch(`${API_BASE}/screenings?limit=${encodeURIComponent(limit)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch screening runs`);
    return await res.json();
  } catch (err) {
    console.warn('[API] Could not fetch screening runs:', err.message);
    return null;
  }
}


/**
 * Fetch detailed screening results for a specific run from the database.
 */
export async function fetchScreeningResults(runId, view = 'all', limit = 250) {
  try {
    const res = await fetch(`${API_BASE}/screenings/${encodeURIComponent(runId)}/results?view=${encodeURIComponent(view)}&limit=${encodeURIComponent(limit)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch run results`);
    return await res.json();
  } catch (err) {
    console.warn(`[API] Could not fetch results for ${runId}:`, err.message);
    return null;
  }
}

/**
 * Fetch delta comparison between two runs from the backend.
 */
export async function fetchRunComparison(runId, prevRunId) {
  try {
    const res = await fetch(`${API_BASE}/screenings/${encodeURIComponent(runId)}/compare/${encodeURIComponent(prevRunId)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch run comparison`);
    return await res.json();
  } catch (err) {
    console.warn(`[API] Could not fetch run comparison:`, err.message);
    return null;
  }
}
