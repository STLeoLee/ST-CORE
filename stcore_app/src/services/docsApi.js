// src/services/docsApi.js
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 180000,
});

const normalizeProject = (p) => ({
  id: p.Id ?? p.id,
  name: p.Name ?? p.name ?? 'Unnamed Project',
  raw: p,
});

export const docsApi = {
  getProjects: async () => {
    const { data } = await apiClient.get('/api/projects');
    if (!Array.isArray(data)) return [];
    return data.map(normalizeProject);
  },

  getDashboardStats: async (projectId, signal) => {
    const params = { project_id: projectId === 'all' ? 25 : projectId };
    const { data } = await apiClient.get('/api/dashboard/stats', { params, signal });
    return data;
  },

  getDashboardCards: async (projectId, boardId = 0, signal) => {
    const params = {
      project_id: projectId === 'all' ? 0 : projectId,
      board_id: boardId,
    };
    const { data } = await apiClient.get('/api/dashboard/cards', { params, signal });
    return data;
  },

  getBoards: async (projectId) => {
    const { data } = await apiClient.get('/api/boards', { params: { project_id: projectId } });
    return Array.isArray(data) ? data : [];
  },

  // Optional: inspect / clear the backend stage cache
  getStagesCache: async () => {
    const { data } = await apiClient.get('/api/stages');
    return data;
  },
  clearStagesCache: async () => {
    const { data } = await apiClient.delete('/api/stages/cache');
    return data;
  },
};