const configuredApiBase = import.meta.env.VITE_API_BASE_URL?.trim();
const API_BASE = (configuredApiBase || '/api/v1').replace(/\/+$/, '');

function unreachableApiError() {
  return new Error(
    `Cannot reach the Flask API at ${API_BASE}. Deploy the backend and set VITE_API_BASE_URL to its public API URL (ending in /api/v1).`
  );
}

async function readErrorResponse(response) {
  let data = null;
  let body = '';
  try {
    body = await response.text();
    data = body ? JSON.parse(body) : null;
  } catch {
    // A proxy or static host often returns an HTML error page instead of JSON.
  }

  const apiMessage = data?.error?.message || data?.warning?.message;
  if (apiMessage) return { data, message: apiMessage };

  if (!data && response.status === 403 && API_BASE.startsWith('/')) {
    return {
      data: null,
      message: 'The local API proxy returned HTTP 403 instead of a Flask API response. Start this project’s backend on port 5001, then reload the page.'
    };
  }

  return {
    data,
    message: data
      ? 'Server request failed'
      : `The API at ${API_BASE} returned HTTP ${response.status}. Verify that this URL points to the deployed Flask API ending in /api/v1.`
  };
}

function getToken() {
  return localStorage.getItem('tapmi_token');
}

function handleExpiredSession(response, endpoint, token) {
  if (response.status !== 401 || !token || endpoint.startsWith('/auth/login')) return;
  setToken(null);
  window.dispatchEvent(new Event('tapmi:unauthorized'));
}

export function setToken(token) {
  if (token) {
    localStorage.setItem('tapmi_token', token);
  } else {
    localStorage.removeItem('tapmi_token');
  }
}

async function getAuthorizedResponse(endpoint) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, { headers });
  } catch {
    throw unreachableApiError();
  }
  if (!response.ok) {
    handleExpiredSession(response, endpoint, token);
    const { message } = await readErrorResponse(response);
    throw new Error(message);
  }

  return response;
}

async function downloadFile(endpoint) {
  const response = await getAuthorizedResponse(endpoint);
  const blob = await response.blob();

  const disposition = response.headers.get('Content-Disposition') || '';
  const filenameMatch = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
  const filename = decodeURIComponent(filenameMatch?.[1] || filenameMatch?.[2] || 'department-roster');
  return { blob, filename };
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers
  };

  if (options.body && typeof options.body === 'object') {
    config.body = JSON.stringify(options.body);
  }

  let response;
  try {
    response = await fetch(url, config);
  } catch {
    throw unreachableApiError();
  }

  if (!response.ok) {
    handleExpiredSession(response, endpoint, token);
    const { data, message } = await readErrorResponse(response);
    const errorObj = new Error(message);
    errorObj.status = response.status;
    errorObj.data = data;
    throw errorObj;
  }

  try {
    return await response.json();
  } catch {
    throw new Error('The Flask API returned an invalid response. Check the backend logs and try again.');
  }
}

export const api = {
  // Auth
  login: (credentials) => request('/auth/login', { method: 'POST', body: credentials }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  requestActivation: (payload) => request('/auth/activation/request', { method: 'POST', body: payload }),
  verifyActivation: (payload) => request('/auth/activation/verify', { method: 'POST', body: payload }),
  completeActivation: (payload) => request('/auth/activation/complete', { method: 'POST', body: payload }),
  getMe: () => request('/me'),

  // Volunteers
  getVolunteers: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/volunteers${q ? `?${q}` : ''}`);
  },
  getVolunteer: (id) => request(`/volunteers/${id}`),
  createVolunteer: (payload) => request('/volunteers', { method: 'POST', body: payload }),
  updateVolunteer: (id, payload) => request(`/volunteers/${id}`, { method: 'PATCH', body: payload }),
  setVolunteerPassword: (id, password) => request(`/volunteers/${id}/password`, { method: 'PUT', body: { password } }),
  getMySkills: () => request('/me/skills'),
  updateMySkills: (skill_ids) => request('/me/skills', { method: 'PUT', body: { skill_ids } }),
  getMyAssignments: () => request('/me/assignments'),
  getMyAssignmentHistory: () => request('/me/assignment-history'),

  // Skills
  getSkills: () => request('/skills'),
  suggestSkill: (payload) => request('/skills/suggestions', { method: 'POST', body: payload }),
  getSuggestions: () => request('/skills/suggestions'),
  approveSuggestion: (id) => request(`/skills/suggestions/${id}/approve`, { method: 'POST' }),
  rejectSuggestion: (id, reason) => request(`/skills/suggestions/${id}/reject`, { method: 'POST', body: { reason } }),

  // Events & Requirements
  getEvents: () => request('/events'),
  getEvent: (id) => request(`/events/${id}`),
  createEvent: (payload) => request('/events', { method: 'POST', body: payload }),
  updateEvent: (id, payload) => request(`/events/${id}`, { method: 'PATCH', body: payload }),
  cancelEvent: (id) => request(`/events/${id}/cancel`, { method: 'POST' }),
  archiveEvent: (id) => request(`/events/${id}/archive`, { method: 'POST' }),
  getRequirements: (eventId) => request(`/events/${eventId}/requirements`),
  updateRequirements: (eventId, requirements) => request(`/events/${eventId}/requirements`, { method: 'PUT', body: { requirements } }),
  calculateCapacity: (eventId, payload) => request(`/events/${eventId}/requirements/calculate`, { method: 'POST', body: payload }),

  // Allocations
  runAllocation: (eventId, payload) => request(`/events/${eventId}/allocations/runs`, { method: 'POST', body: payload }),
  getEventAllocations: (eventId) => request(`/events/${eventId}/allocations`),
  getAllocationVersion: (versionId) => request(`/allocations/${versionId}`),
  editAssignment: (versionId, payload) => request(`/allocations/${versionId}/assignments`, { method: 'PATCH', body: payload }),
  approveAllocation: (versionId, comment) => request(`/allocations/${versionId}/approve`, { method: 'POST', body: { comment } }),
  rejectAllocation: (versionId, comment) => request(`/allocations/${versionId}/reject`, { method: 'POST', body: { comment } }),
  publishAllocation: (versionId) => request(`/allocations/${versionId}/publish`, { method: 'POST' }),
  regenerateAllocation: (versionId, payload) => request(`/allocations/${versionId}/regenerate`, { method: 'POST', body: payload }),

  // Reports & Logs
  getStaffingReport: (eventId, versionId) => request(`/events/${eventId}/reports/staffing${versionId ? `?version_id=${versionId}` : ''}`),
  getUnderutilizationReport: (eventId, versionId) => request(`/events/${eventId}/reports/underutilization${versionId ? `?version_id=${versionId}` : ''}`),
  getAlgorithmComparison: (eventId) => request(`/events/${eventId}/reports/algorithm-comparison`),
  getRecommendations: (eventId) => request(`/events/${eventId}/reports/recommendations`),
  getReportChart: async (eventId) => (await getAuthorizedResponse(`/events/${eventId}/reports/chart`)).blob(),
  downloadRoster: (eventId, format = 'xlsx') => downloadFile(`/events/${eventId}/reports/roster?format=${encodeURIComponent(format)}`),
  getAuditLog: () => request('/audit-log'),

  // Core Committee management and dashboards
  getCoreCommitteeMembers: () => request('/core-committee/members'),
  createCoreCommitteeMember: (payload) => request('/core-committee/members', { method: 'POST', body: payload }),
  setCoreCommitteePassword: (id, password) => request(`/core-committee/members/${id}/password`, { method: 'PUT', body: { password } }),
  getEventDepartmentHeads: (eventId) => request(`/events/${eventId}/department-heads`),
  saveEventDepartmentHeads: (eventId, assignments) => request(`/events/${eventId}/department-heads`, { method: 'PUT', body: { assignments } }),
  getMyDepartmentAssignments: () => request('/me/department-assignments'),

  // Simulations
  runSimulation: (eventId, payload) => request(`/events/${eventId}/simulations`, { method: 'POST', body: payload })
};
