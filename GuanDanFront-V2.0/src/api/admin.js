import { request } from '../api.js';

const jsonPost = (path, payload = {}) => request(path, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(payload),
});

export const getAdminOverview = () => request('/api/admin/overview');

export const importRegistration = (file) => {
  const formData = new FormData();
  formData.append('file', file);

  return request('/api/admin/import', {
    method: 'POST',
    body: formData,
  });
};

export const clearBusinessData = () => request('/api/admin/clear', { method: 'POST' });

export const setAdminTurn = (turn) => jsonPost('/api/admin/turn', { turn });

export const startAdminTimer = () => request('/api/admin/timer/start', { method: 'POST' });

export const stopAdminTimer = () => request('/api/admin/timer/stop', { method: 'POST' });

export const getAdminMatches = () => request('/api/admin/matches');

export const generateAdminMatches = () => request('/api/admin/matches/generate', { method: 'POST' });

export const getAdminScoreMatch = ({ turn, table }) => {
  const params = new URLSearchParams({ turn, table });
  return request(`/api/admin/score-match?${params.toString()}`);
};

export const submitAdminScore = (payload) => jsonPost('/api/admin/scores', payload);
