import { request } from '../api.js';

const jsonPost = (path, payload = {}) => request(path, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(payload),
});

export const getCurrentScoreTurn = () => request('/api/score/current-turn');

export const getScoreTable = (table) => {
  const params = new URLSearchParams({ table });
  return request(`/api/score/table?${params.toString()}`);
};

export const submitScoreTable = (payload) => jsonPost('/api/score/table', payload);
