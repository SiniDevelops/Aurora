export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  skill?: string;
  timestamp: string;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

export interface Note {
  path: string;
  content: string;
  frontmatter: Record<string, any>;
  lastModified: string;
}

export interface NoteLink {
  source: string;
  target: string;
}

export interface VaultContext {
  activeNotes: string[];
  searchQuery?: string;
}

export interface SkillMetadata {
  name: string;
  description: string;
  parameters: any;
}

export interface ChatRequest {
  message: string;
  sessionId?: string;
  context?: VaultContext;
}

export interface ChatResponse {
  message: ChatMessage;
  sessionId: string;
}

export interface NoteResponse {
  note: Note;
}

export interface VaultTreeResponse {
  tree: any; // Simplified for now
}

export interface WSMessage {
  type: string;
  payload: any;
}

export interface WSTokenMessage extends WSMessage {
  type: 'token';
  payload: { token: string };
}

export interface WSStartMessage extends WSMessage {
  type: 'start';
  payload: { messageId: string; role: string };
}

export interface WSEndMessage extends WSMessage {
  type: 'end';
  payload: { messageId: string; fullContent: string };
}

export interface WSErrorMessage extends WSMessage {
  type: 'error';
  payload: { message: string; code: string };
}
