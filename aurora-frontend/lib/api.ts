const API_BASE = '';

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export const chatApi = {
  sendMessage: (data: any) => apiFetch('/api/chat/message', { method: 'POST', body: JSON.stringify(data) }),
  getHistory: (sessionId: string) => apiFetch(`/api/chat/session/${sessionId}`),
  deleteSession: (sessionId: string) => apiFetch(`/api/chat/session/${sessionId}`, { method: 'DELETE' }),
  listSessions: () => apiFetch('/api/chat/sessions'),
};

export const vaultApi = {
  getTree: () => apiFetch('/api/vault/tree'),
  getNote: (path: string) => apiFetch(`/api/vault/note/${encodeURIComponent(path)}`),
  createNote: (data: any) => apiFetch('/api/vault/note', { method: 'POST', body: JSON.stringify(data) }),
  updateNote: (path: string, data: any) => apiFetch(`/api/vault/note/${encodeURIComponent(path)}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteNote: (path: string) => apiFetch(`/api/vault/note/${encodeURIComponent(path)}`, { method: 'DELETE' }),
  search: (query: string) => apiFetch(`/api/vault/search?q=${encodeURIComponent(query)}`),
  reindex: () => apiFetch('/api/vault/reindex', { method: 'POST' }),
  getStats: () => apiFetch('/api/vault/stats'),
};

export const settingsApi = {
  getSettings: () => apiFetch('/api/settings'),
  updateSettings: (data: any) => apiFetch('/api/settings', { method: 'PUT', body: JSON.stringify(data) }),
  getPrivacy: () => apiFetch('/api/settings/privacy'),
  updatePrivacy: (data: any) => apiFetch('/api/settings/privacy', { method: 'PUT', body: JSON.stringify(data) }),
  getLLMProviders: () => apiFetch('/api/settings/llm/providers'),
  getActiveLLM: () => apiFetch('/api/settings/llm/active'),
};
