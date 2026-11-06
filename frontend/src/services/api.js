/**
 * API service for communicating with the FastAPI screening backend.
 */

const API_BASE = '/api';

// ============================================================================
// AUTHENTICATION HELPERS
// ============================================================================

export function getStoredAuthToken() {
  return localStorage.getItem('access_token') || null;
}

export function getAuthHeaders(extraHeaders = {}) {
  const token = getStoredAuthToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extraHeaders,
  };
}

/**
 * Fetch the canonical catalog of all 16 screening metrics and their limits.
 */
export async function fetchRuleCatalog() {
  try {
    const res = await fetch(`${API_BASE}/rules/catalog`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch rule catalog`);
    return await res.json();
  } catch (err) {
    console.warn('[API] Could not fetch rule catalog from backend:', err.message);
    return null;
  }
}

/**
 * Fetch all saved rule profiles from PostgreSQL for current user.
 */
export async function fetchProfiles() {
  try {
    const res = await fetch(`${API_BASE}/rules/profiles`, {
      headers: getAuthHeaders(),
    });
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
      headers: getAuthHeaders(),
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
      headers: getAuthHeaders(),
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
      headers: getAuthHeaders(),
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
      headers: getAuthHeaders(),
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
      headers: getAuthHeaders(),
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
    const res = await fetch(`${API_BASE}/screenings?limit=${encodeURIComponent(limit)}`, {
      headers: getAuthHeaders(),
    });
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
    const res = await fetch(
      `${API_BASE}/screenings/${encodeURIComponent(runId)}/results?view=${encodeURIComponent(view)}&limit=${encodeURIComponent(limit)}`,
      {
        headers: getAuthHeaders(),
      }
    );
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
    const res = await fetch(
      `${API_BASE}/screenings/${encodeURIComponent(runId)}/compare/${encodeURIComponent(prevRunId)}`,
      {
        headers: getAuthHeaders(),
      }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch run comparison`);
    return await res.json();
  } catch (err) {
    console.warn(`[API] Could not fetch run comparison:`, err.message);
    return null;
  }
}

/**
 * Fetch funnel counts (Universe -> Markets -> Floors -> Gates -> Score -> Shortlist -> Selected) for a run.
 */
export async function fetchRunFunnel(runId) {
  try {
    const res = await fetch(`${API_BASE}/screenings/${encodeURIComponent(runId)}/funnel`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn(`[API] Could not fetch funnel for ${runId}:`, err.message);
    return null;
  }
}

/**
 * =========================================================================
 * PHASE 15: HOLDINGS IMPORT AND STORAGE API METHODS
 * =========================================================================
 */

/**
 * Upload a CSV or Excel holdings file to the backend for ingestion into PostgreSQL.
 */
export async function uploadHoldingsFile(file, portfolioName = 'Core Equity Fund') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('portfolio_name', portfolioName);

  try {
    const token = getStoredAuthToken();
    const res = await fetch(`${API_BASE}/holdings/import`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}: Upload failed`);
    }
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to upload holdings file:', err.message);
    throw err;
  }
}

/**
 * Fetch all persistent portfolio holdings from PostgreSQL.
 */
export async function fetchHoldings(portfolioName = null) {
  try {
    const url = portfolioName
      ? `${API_BASE}/holdings?portfolio_name=${encodeURIComponent(portfolioName)}`
      : `${API_BASE}/holdings`;
    const res = await fetch(url, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch holdings`);
    return await res.json();
  } catch (err) {
    console.warn('[API] Could not fetch holdings:', err.message);
    return [];
  }
}

/**
 * Fetch portfolio allocation and diversification summary.
 */
export async function fetchHoldingsSummary(portfolioName = 'Core Equity Fund') {
  try {
    const res = await fetch(`${API_BASE}/holdings/summary?portfolio_name=${encodeURIComponent(portfolioName)}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch holdings summary`);
    return await res.json();
  } catch (err) {
    console.warn('[API] Could not fetch holdings summary:', err.message);
    return null;
  }
}

/**
 * Manually add a position to the portfolio.
 */
export async function addManualHolding(holdingData) {
  try {
    const res = await fetch(`${API_BASE}/holdings`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(holdingData),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to create holding`);
    }
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to create holding:', err.message);
    throw err;
  }
}

/**
 * Delete a single holding by ID from PostgreSQL.
 */
export async function deleteHolding(holdingId) {
  try {
    const res = await fetch(`${API_BASE}/holdings/${encodeURIComponent(holdingId)}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to delete holding`);
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to delete holding:', err.message);
    throw err;
  }
}

/**
 * Clear all holdings from a portfolio in PostgreSQL.
 */
export async function clearHoldings(portfolioName = null) {
  try {
    const url = portfolioName
      ? `${API_BASE}/holdings?portfolio_name=${encodeURIComponent(portfolioName)}`
      : `${API_BASE}/holdings`;
    const res = await fetch(url, { method: 'DELETE', headers: getAuthHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to clear holdings`);
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to clear holdings:', err.message);
    throw err;
  }
}

/**
 * Record or update an analyst Keep/Drop decision in PostgreSQL (Phase 16).
 */
export async function recordDecisionApi(decisionData) {
  try {
    const res = await fetch(`${API_BASE}/decisions`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(decisionData),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to record decision`);
    }
    return await res.json();
  } catch (err) {
    console.warn('[API] Could not persist decision to backend:', err.message);
    return null;
  }
}

/**
 * Fetch recorded analyst decisions from PostgreSQL (Phase 16).
 */
export async function fetchDecisionsApi(runId = null, profileName = null) {
  try {
    const params = new URLSearchParams();
    if (runId) params.append('run_id', runId);
    if (profileName) params.append('profile_name', profileName);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/decisions${qs}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch decisions`);
    return await res.json();
  } catch (err) {
    console.warn('[API] Could not fetch decisions:', err.message);
    return [];
  }
}

/**
 * Bulk-sync all analyst Keep/Drop decisions upon Excel export to PostgreSQL (Phase 16).
 */
export async function syncDecisionsApi({ profile_name, run_id, decisions }) {
  try {
    const res = await fetch(`${API_BASE}/decisions/sync`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ profile_name, run_id, decisions }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to sync decisions`);
    }
    return await res.json();
  } catch (err) {
    console.warn('[API] Could not sync decisions to backend:', err.message);
    return null;
  }
}

/**
 * Phase 17: Fetch screening schedule configuration and upcoming next runs from backend.
 */
export async function fetchScheduleConfig() {
  try {
    const res = await fetch(`${API_BASE}/schedules`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch schedule`);
    return await res.json();
  } catch (err) {
    console.warn('[API] Could not fetch schedule:', err.message);
    return null;
  }
}

/**
 * Phase 17: Save screening schedule configuration to backend.
 */
export async function saveScheduleConfig(config) {
  try {
    const res = await fetch(`${API_BASE}/schedules`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(config),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to save schedule`);
    }
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to save schedule:', err.message);
    throw err;
  }
}

/**
 * Delete a screening schedule from backend (Phase 17).
 */
export async function deleteScheduleConfig(scheduleId) {
  try {
    const res = await fetch(`${API_BASE}/schedules/${encodeURIComponent(scheduleId)}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to delete schedule`);
    }
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to delete schedule:', err.message);
    throw err;
  }
}

/**
 * Permanently delete a screening run and its results from backend.
 */
export async function deleteScreeningRun(runId) {
  try {
    const res = await fetch(`${API_BASE}/screenings/${encodeURIComponent(runId)}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to delete screening run`);
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
    const res = await fetch(`${API_BASE}/screenings`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to clear screening runs`);
    }
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to clear screening runs:', err.message);
    throw err;
  }
}

/**
 * Remove a specific day (e.g. 'wed') from a schedule's active days.
 */
export async function removeScheduleDay(scheduleId, day) {
  try {
    const res = await fetch(`${API_BASE}/schedules/${encodeURIComponent(scheduleId)}/days/${encodeURIComponent(day)}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}: Failed to remove day`);
    }
    return await res.json();
  } catch (err) {
    console.error('[API] Failed to remove day from schedule:', err.message);
    throw err;
  }
}

// ============================================================================
// AUTHENTICATION API SERVICES (Phase 5)
// ============================================================================

export async function loginApi(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const error = new Error(err.detail || 'Login failed. Please check your credentials.');
    error.status = res.status;
    throw error;
  }
  return await res.json();
}

export async function signupApi(email, password, fullName = '') {
  const res = await fetch(`${API_BASE}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const error = new Error(err.detail || 'Sign up failed. Please try again.');
    error.status = res.status;
    throw error;
  }
  return await res.json();
}

export async function fetchMeApi(token) {
  const authToken = token || getStoredAuthToken();
  if (!authToken) throw new Error('No authentication token available');

  const res = await fetch(`${API_BASE}/auth/me`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const error = new Error(err.detail || 'Session expired or invalid');
    error.status = res.status;
    throw error;
  }
  return await res.json();
}

export async function pingSessionApi(token) {
  const authToken = token || getStoredAuthToken();
  if (!authToken) return null;

  try {
    const res = await fetch(`${API_BASE}/auth/ping`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function logoutApi(token) {
  const authToken = token || getStoredAuthToken();
  if (!authToken) return { message: 'Logged out' };

  try {
    const res = await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
    return await res.json();
  } catch {
    return { message: 'Logged out' };
  }
}


export async function verifyEmailApi(email, code) {
  const res = await fetch(`${API_BASE}/auth/verify-email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, code }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Email verification failed.');
  }
  return await res.json();
}

export async function resendVerificationApi(email) {
  const res = await fetch(`${API_BASE}/auth/resend-verification`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to resend verification code.');
  }
  return await res.json();
}

export async function forgotPasswordApi(email) {
  const res = await fetch(`${API_BASE}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to request password reset.');
  }
  return await res.json();
}

export async function resetPasswordApi(email, code, newPassword) {
  const res = await fetch(`${API_BASE}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, code, new_password: newPassword }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Password reset failed.');
  }
  return await res.json();
}

export async function changePasswordApi(currentPassword, newPassword) {
  const authToken = getStoredAuthToken();
  if (!authToken) throw new Error('Not authenticated');

  const res = await fetch(`${API_BASE}/auth/change-password`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to change password.');
  }
  return await res.json();
}

export async function updateProfileApi(fullName) {
  const authToken = getStoredAuthToken();
  if (!authToken) throw new Error('Not authenticated');

  const res = await fetch(`${API_BASE}/auth/profile`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify({ full_name: fullName }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to update profile.');
  }
  return await res.json();
}
