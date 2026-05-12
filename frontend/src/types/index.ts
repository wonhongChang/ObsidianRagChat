// 백엔드 Pydantic Message 모델과 1:1 — 이것만 API로 전송
export interface ApiMessage {
  role: 'user' | 'assistant';
  content: string;
}

// UI 전용 확장 — API로 절대 보내지 않음
export interface Message extends ApiMessage {
  id: string;
  sources?: Source[];
  usage?: TokenUsage;
  elapsedTime?: number;
  cached?: boolean;
  model?: ChatModel;
  responseLanguage?: ResponseLanguage;
  streaming?: boolean;
}

export interface Source {
  filename: string;
  score: number;
  tags: string[];
  section?: string;
  text?: string;
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export type ChatModel = 'gpt-4o-mini' | 'gpt-5-mini';
export type ResponseLanguage = 'auto' | 'ko' | 'en' | 'ja';

export interface ChatSettings {
  topK: number;
  ignoreTokenLimit: boolean;
  model: ChatModel;
  responseLanguage: ResponseLanguage;
}
