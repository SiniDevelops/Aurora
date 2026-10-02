import { create } from 'zustand';
import { ChatMessage } from './types';

interface ChatStore {
  messages: ChatMessage[];
  sessionId: string | null;
  isStreaming: boolean;
  addMessage: (msg: ChatMessage) => void;
  setStreaming: (streaming: boolean) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  sessionId: null,
  isStreaming: false,
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  setStreaming: (streaming) => set({ isStreaming: streaming }),
  clearMessages: () => set({ messages: [] }),
}));

interface VaultStore {
  tree: any;
  activeNote: string | null;
  setTree: (tree: any) => void;
  setActiveNote: (note: string | null) => void;
}

export const useVaultStore = create<VaultStore>((set) => ({
  tree: null,
  activeNote: null,
  setTree: (tree) => set({ tree }),
  setActiveNote: (note) => set({ activeNote: note }),
}));

interface SettingsStore {
  settings: any;
  theme: 'light' | 'dark';
  setSettings: (settings: any) => void;
  toggleTheme: () => void;
}

export const useSettingsStore = create<SettingsStore>((set) => ({
  settings: null,
  theme: 'dark',
  setSettings: (settings) => set({ settings }),
  toggleTheme: () => set((state) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
}));

interface AppStore {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}

export const useAppStore = create<AppStore>((set) => ({
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
