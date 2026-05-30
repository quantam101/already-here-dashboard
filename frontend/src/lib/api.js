import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

export const revenueAPI = {
  getAll: () => api.get("/revenue/"),
  getStats: () => api.get("/revenue/stats/overview"),
  getById: (id) => api.get(`/revenue/${id}`),
  create: (data) => api.post("/revenue/", data),
  update: (id, data) => api.patch(`/revenue/${id}`, data),
  delete: (id) => api.delete(`/revenue/${id}`),
};

export const contentAPI = {
  getAll: (params) => api.get("/content/", { params }),
  getById: (id) => api.get(`/content/${id}`),
  generate: (data) => api.post("/content/generate", data),
  update: (id, data) => api.patch(`/content/${id}`, data),
  delete: (id) => api.delete(`/content/${id}`),
};

export const studioAPI = {
  getIdeas: () => api.get("/studio/ideas/"),
  createIdea: (data) => api.post("/studio/ideas/", data),
  generateScript: (ideaId) => api.post(`/studio/ideas/${ideaId}/script`),
  scriptsForIdea: (ideaId) => api.get(`/studio/ideas/${ideaId}/scripts`),
  allScripts: () => api.get("/studio/scripts/"),
  getConnectors: () => api.get("/studio/connectors/"),
  getScheduled: () => api.get("/studio/schedule/"),
};

export const agentsAPI = {
  getAll: (params) => api.get("/agents/", { params }),
  getById: (id) => api.get(`/agents/${id}`),
  create: (data) => api.post("/agents/", data),
  update: (id, data) => api.patch(`/agents/${id}`, data),
  execute: (id) => api.post(`/agents/${id}/execute`),
};

export const buildsAPI = {
  getAll: (params) => api.get("/builds/", { params }),
  getById: (id) => api.get(`/builds/${id}`),
  create: (data) => api.post("/builds/", data),
  update: (id, data) => api.patch(`/builds/${id}`, data),
};

export const deploymentsAPI = {
  getAll: (params) => api.get("/deployments/", { params }),
  getById: (id) => api.get(`/deployments/${id}`),
  create: (data) => api.post("/deployments/", data),
  update: (id, data) => api.patch(`/deployments/${id}`, data),
};

export const approvalsAPI = {
  getAll: (params) => api.get("/approvals/", { params }),
  getById: (id) => api.get(`/approvals/${id}`),
  create: (data) => api.post("/approvals/", data),
  decide: (id, data) => api.post(`/approvals/${id}/decide`, data),
};

export const auditAPI = {
  getAll: (params) => api.get("/audit/", { params }),
  getStats: () => api.get("/audit/stats"),
};

export const healthAPI = {
  check: () => api.get("/health"),
  checkService: (service, url) => api.get(`/health/check/${service}`, { params: { url } }),
  getHistory: (params) => api.get("/health/history", { params }),
};

export const ledgerAPI = {
  getAll: (params) => api.get("/ledger/", { params }),
  create: (data) => api.post("/ledger/", data),
  progress: () => api.get("/ledger/stats/profit-progress"),
  byStream: () => api.get("/ledger/stats/by-stream"),
};

export const publishingAPI = {
  getAll: (params) => api.get("/publishing/", { params }),
  create: (data) => api.post("/publishing/", data),
  update: (id, data) => api.patch(`/publishing/${id}`, data),
  stats: () => api.get("/publishing/stats/overview"),
};

export const scoutAPI = {
  viral: (params) => api.get("/scout/viral", { params }),
  grants: (params) => api.get("/scout/grants", { params }),
  contracts: (params) => api.get("/scout/contracts", { params }),
  news: (params) => api.get("/scout/news", { params }),
  sources: () => api.get("/scout/sources"),
};

export const proposalsAPI = {
  getAll: (params) => api.get("/proposals/", { params }),
  getById: (id) => api.get(`/proposals/${id}`),
  draft: (data) => api.post("/proposals/draft", data),
  invoice: (data) => api.post("/proposals/invoice", data),
  update: (id, data) => api.patch(`/proposals/${id}`, data),
  stats: () => api.get("/proposals/stats/overview"),
};

export const ledgerImportCSV = async (streamId, file) => {
  const form = new FormData();
  form.append("stream_id", streamId);
  form.append("file", file);
  const res = await fetch(`${API}/ledger/import-csv`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

export const paymentsAPI = {
  packages: () => api.get("/payments/packages"),
  checkout: (data) => api.post("/payments/checkout", data),
  status: (sessionId) => api.get(`/payments/checkout/${sessionId}`),
  transactions: () => api.get("/payments/transactions"),
  stats: () => api.get("/payments/stats"),
};

export const analyticsAPI = {
  dashboard: () => api.get("/analytics/dashboard"),
  funnel: () => api.get("/analytics/funnel"),
  postingTimes: () => api.get("/analytics/posting-times"),
  streamRoi: () => api.get("/analytics/stream-roi"),
  platformMix: () => api.get("/analytics/platform-mix"),
  viralThemes: () => api.get("/analytics/viral-themes"),
  momentum: () => api.get("/analytics/momentum"),
};

export const advisorAPI = {
  recommend: () => api.post("/advisor/recommend"),
  recent: () => api.get("/advisor/recent"),
};

export const booksAPI = {
  getAll: (params) => api.get("/books/", { params }),
  getById: (id) => api.get(`/books/${id}`),
  create: (data) => api.post("/books/", data),
  delete: (id) => api.delete(`/books/${id}`),
  stats: () => api.get("/books/stats/overview"),
  downloadMd: (id) => `${API}/books/${id}/download.md`,
  downloadTxt: (id) => `${API}/books/${id}/download.txt`,
  downloadMp3: (id, voiceId) => `${API}/books/${id}/audio.mp3${voiceId ? `?voice_id=${encodeURIComponent(voiceId)}` : ""}`,
};

export const authAPI = {
  config: () => api.get("/auth/config"),
  me: () => api.get("/auth/me"),
  login: (body) => api.post("/auth/login", body),
  logout: () => api.post("/auth/logout"),
};

export const systemAPI = {
  status: () => api.get("/system/status"),
};

export const secretsAPI = {
  status: () => api.get("/secrets/status"),
  items: () => api.get("/secrets/items"),
};

export const distillationAPI = {
  stats: () => api.get("/distillation/stats"),
  config: () => api.get("/distillation/config"),
  budget: () => api.get("/distillation/budget"),
  budgetHistory: (days = 14) => api.get(`/distillation/budget/history?days=${days}`),
  clear: () => api.post("/distillation/clear"),
};


// Faceless Video Engine
export const videoAPI = {
  config: () => api.get("/video/config"),
  voices: () => api.get("/video/voices"),
  music: () => api.get("/video/music"),
  render: (payload) => api.post("/video/render", payload),
  renderFromScript: (scriptId, voiceId, mode = "faceless", portraitId = null) =>
    api.post("/video/render-from-script", {
      script_id: scriptId, voice_id: voiceId, mode, portrait_id: portraitId,
    }),
  jobs: (limit = 30) => api.get(`/video/jobs?limit=${limit}`),
  job: (id) => api.get(`/video/jobs/${id}`),
  downloadUrl: (id) => `${BACKEND_URL}/api/video/jobs/${id}/download`,
  deleteJob: (id) => api.delete(`/video/jobs/${id}`),
  uploadPortrait: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post("/video/portraits/upload", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  listPortraits: () => api.get("/video/portraits"),
  deletePortrait: (id) => api.delete(`/video/portraits/${id}`),
};

export const hooksAPI = {
  generate: (payload) => api.post("/hooks/", payload),
  abTest: (payload) => api.post("/hooks/ab-test", payload),
};

// Governance (L0-L5 + HITL approval queue)
export const governanceAPI = {
  status: () => api.get("/governance/status"),
  manifest: () => api.get("/governance/manifest"),
  reload: () => api.post("/governance/manifest/reload"),
  approvals: (status) => api.get("/governance/approvals" + (status ? `?status=${status}` : "")),
  approve: (id, note = "", actor = "operator") => api.post(`/governance/approvals/${id}/approve`, { note, actor }),
  reject: (id, note = "", actor = "operator") => api.post(`/governance/approvals/${id}/reject`, { note, actor }),
};

// Master Revenue Equation tracker (Q_D × C_R × A_OV × P_F × F_C × P_M)
export const revenueEquationAPI = {
  equation: () => api.get("/revenue-equation/equation"),
  bottleneck: () => api.get("/revenue-equation/bottleneck"),
};

// Lifelong Catch and Correct telemetry
export const lcacAPI = {
  scan: () => api.get("/lifelong-catch-correct/"),
};
