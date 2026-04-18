import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Leads API
export const leadsAPI = {
  getAll: (params) => api.get('/api/leads', { params }),
  getById: (leadId) => api.get(`/api/leads/${leadId}`),
  create: (data) => api.post('/api/leads', data),
  update: (leadId, data) => api.put(`/api/leads/${leadId}`, data),
  delete: (leadId) => api.delete(`/api/leads/${leadId}`),
  bulkUpdate: (leadIds, updates) => api.post('/api/leads/bulk-update', { lead_ids: leadIds, updates }),

  // Notes
  getNotes: (leadId) => api.get(`/api/leads/${leadId}/notes`),
  addNote: (leadId, data) => api.post(`/api/leads/${leadId}/notes`, data),

  // Full lead timeline
  getTimeline: (leadId) => api.get(`/api/leads/${leadId}/timeline`),

  // Communication
  sendWhatsApp: (leadId, message) => api.post(`/api/leads/${leadId}/send-whatsapp`, { message }),
  sendEmail: (leadId, subject, body) => api.post(`/api/leads/${leadId}/send-email`, { subject, body }),
};

// Monitoring API
export const monitoringAPI = {
  getDailyActivity: (date, counselor) =>
    api.get('/api/monitoring/daily-activity', { params: { date, counselor } }),
  getActivityLog: (params) =>
    api.get('/api/monitoring/activity-log', { params }),
  getCounselorSummary: (from_date, to_date) =>
    api.get('/api/monitoring/counselor-summary', { params: { from_date, to_date } }),
};

// Dashboard API
export const dashboardAPI = {
  getStats: () => api.get('/api/dashboard/stats'),
};

// Analytics API
export const analyticsAPI = {
  getRevenueByCountry: () => api.get('/api/analytics/revenue-by-country'),
  getConversionFunnel: () => api.get('/api/analytics/conversion-funnel'),
};

// Hospitals API
export const hospitalsAPI = {
  getAll: (params) => api.get('/api/hospitals', { params }),
  create: (data) => api.post('/api/hospitals', data),
};

// Courses API
export const coursesAPI = {
  getAll: (params) => api.get('/api/courses', { params }),
  create: (data) => api.post('/api/courses', data),
};

// Counselors API
export const counselorsAPI = {
  getAll: () => api.get('/api/counselors'),
};

// Users API
export const usersAPI = {
  getAll: () => api.get('/api/users'),
  getById: (userId) => api.get(`/api/users/${userId}`),
  create: (data) => api.post('/api/users', data),
  update: (userId, data) => api.put(`/api/users/${userId}`, data),
  delete: (userId) => api.delete(`/api/users/${userId}`),
};

// Google Sheet Sync API
export const sheetSyncAPI = {
  getStatus: (apiKey) =>
    api.get('/api/webhook/sheet-sync/status', { params: { api_key: apiKey } }),
  sync: (apiKey, headers, rows, sheetName) =>
    api.post(`/api/webhook/sheet-sync?api_key=${apiKey}`, { headers, rows, sheet_name: sheetName }),
};

export default api;
