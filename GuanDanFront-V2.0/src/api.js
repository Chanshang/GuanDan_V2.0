const BASE_URL = import.meta.env.VITE_BASE_API;
const PORT = import.meta.env.VITE_BASE_PORT;
const DEFAULT_REQUEST_TIMEOUT_MS = 5000;

export async function request(path, options = {}) {
  const { timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS, ...fetchOptions } = options;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${BASE_URL}:${PORT}${path}`, {
      ...fetchOptions,
      signal: fetchOptions.signal || controller.signal,
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status} - ${res.statusText}`);
    }
    return res.json();
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new Error(`请求超时：${timeoutMs}ms`);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
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
