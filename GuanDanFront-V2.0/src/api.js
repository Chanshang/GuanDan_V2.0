const BASE_URL = import.meta.env.VITE_BASE_API;
const PORT = import.meta.env.VITE_BASE_PORT;

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}:${PORT}${path}`, options);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} - ${res.statusText}`);
  }
  return res.json();
}

// Legacy endpoints (kept for fallback / compatibility)
// export const getTurnInfo = () => request('/TURNsinfo');
// export const getOfficeScore = () => request('/officescore');
// export const getTeamInfo = () => request('/sumteaminfo');
// export const getMatchInfo = () => request('/matchesinfo');
// export const getScoresInfo = () => request('/scoresinfo');
// export const getTimeInfo = () => request('/timesinfo');

// Single snapshot endpoint that returns all dashboard data
export const getDashboardSnapshot = () => request('/dashboard_snapshot');
