import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// Revenue API
export const revenueAPI = {
  getAll: () => api.get("/revenue/"),
  getStats: () => api.get("/revenue/stats/overview"),
  getById: (id) => api.get(`/revenue/${id}`),
  create: (data) => api.post("/revenue/", data),
  update: (id, data) => api.patch(`/revenue/${id}`, data),
  delete: (id) => api.delete(`/revenue/${id}`),
};

// Content API
export const contentAPI = {
  getAll: (params) => api.get("/content/", { params }),
  getById: (id) => api.get(`/content/${id}`),
  generate: (data) => api.post("/content/generate", data),
  update: (id, data) => api.patch(`/content/${id}`, data),
  delete: (id) => api.delete(`/content/${id}`),
};

// Agents API
export const agentsAPI = {
  getAll: (params) => api.get("/agents/", { params }),
  getById: (id) => api.get(`/agents/${id}`),
  create: (data) => api.post("/agents/", data),
  update: (id, data) => api.patch(`/agents/${id}`, data),
  execute: (id) => api.post(`/agents/${id}/execute`),
};

// Builds API
export const buildsAPI = {
  getAll: (params) => api.get("/builds/", { params }),
  getById: (id) => api.get(`/builds/${id}`),
  create: (data) => api.post("/builds/", data),
  update: (id, data) => api.patch(`/builds/${id}`, data),
};

// Deployments API
export const deploymentsAPI = {
  getAll: (params) => api.get("/deployments/", { params }),
  getById: (id) => api.get(`/deployments/${id}`),
  create: (data) => api.post("/deployments/", data),
  update: (id, data) => api.patch(`/deployments/${id}`, data),
};

// Approvals API
export const approvalsAPI = {
  getAll: (params) => api.get("/approvals/", { params }),
  getById: (id) => api.get(`/approvals/${id}`),
  create: (data) => api.post("/approvals/", data),
  decide: (id, data) => api.post(`/approvals/${id}/decide`, data),
};

// Audit API
export const auditAPI = {
  getAll: (params) => api.get("/audit/", { params }),
  getStats: () => api.get("/audit/stats"),
};

// Health API
export const healthAPI = {
  check: () => api.get("/health"),
  checkService: (service, url) =>
    api.get(`/health/check/${service}`, { params: { url } }),
  getHistory: (params) => api.get("/health/history", { params }),
};

// Ledger API - proof-of-work revenue entries
export const ledgerAPI = {
  getAll: (params) => api.get("/ledger/", { params }),
  create: (data) => api.post("/ledger/", data),
  progress: () => api.get("/ledger/stats/profit-progress"),
  byStream: () => api.get("/ledger/stats/by-stream"),
};

// Publishing API - proof-of-work content distribution log
export const publishingAPI = {
  getAll: (params) => api.get("/publishing/", { params }),
  create: (data) => api.post("/publishing/", data),
  update: (id, data) => api.patch(`/publishing/${id}`, data),
  stats: () => api.get("/publishing/stats/overview"),
};

// Scout API - free opportunity scraper
export const scoutAPI = {
  viral: (params) => api.get("/scout/viral", { params }),
  grants: (params) => api.get("/scout/grants", { params }),
  contracts: (params) => api.get("/scout/contracts", { params }),
  news: (params) => api.get("/scout/news", { params }),
  sources: () => api.get("/scout/sources"),
};

// Proposals API - grant/contract/invoice writer
export const proposalsAPI = {
  getAll: (params) => api.get("/proposals/", { params }),
  getById: (id) => api.get(`/proposals/${id}`),
  draft: (data) => api.post("/proposals/draft", data),
  invoice: (data) => api.post("/proposals/invoice", data),
  update: (id, data) => api.patch(`/proposals/${id}`, data),
  stats: () => api.get("/proposals/stats/overview"),
};

// CSV import for ledger (multipart)
export const ledgerImportCSV = async (streamId, file) => {
  const form = new FormData();
  form.append("stream_id", streamId);
  form.append("file", file);
  const res = await fetch(`${API}/ledger/import-csv`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

// Payments
export const paymentsAPI = {
  packages: () => api.get("/payments/packages"),
  checkout: (data) => api.post("/payments/checkout", data),
  status: (sessionId) => api.get(`/payments/checkout/${sessionId}`),
  transactions: () => api.get("/payments/transactions"),
  stats: () => api.get("/payments/stats"),
};

// Analytics
export const analyticsAPI = {
  dashboard: () => api.get("/analytics/dashboard"),
  funnel: () => api.get("/analytics/funnel"),
  postingTimes: () => api.get("/analytics/posting-times"),
  streamRoi: () => api.get("/analytics/stream-roi"),
  platformMix: () => api.get("/analytics/platform-mix"),
  viralThemes: () => api.get("/analytics/viral-themes"),
  momentum: () => api.get("/analytics/momentum"),
};

// AI Advisor
export const advisorAPI = {
  recommend: () => api.post("/advisor/recommend"),
  recent: () => api.get("/advisor/recent"),
};

// Books
export const booksAPI = {
  getAll: (params) => api.get("/books/", { params }),
  getById: (id) => api.get(`/books/${id}`),
  create: (data) => api.post("/books/", data),
  delete: (id) => api.delete(`/books/${id}`),
  stats: () => api.get("/books/stats/overview"),
  downloadMd: (id) => `${API}/books/${id}/download.md`,
  downloadTxt: (id) => `${API}/books/${id}/download.txt`,
};

// Auth (optional - only used if backend has OPERATOR_EMAIL set)
export const authAPI = {
  config: () => api.get("/auth/config"),
  me: () => api.get("/auth/me"),
  session: (sessionId) => api.post("/auth/session", { session_id: sessionId }),
  logout: () => api.post("/auth/logout"),
};