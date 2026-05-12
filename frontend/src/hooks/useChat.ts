import { create } from 'zustand';
import { streamSSE } from '../api/stream';
import type { ApiMessage, ChatSettings, Message, Source, TokenUsage } from '../types';

interface ChatStore {
  messages: Message[];
  isStreaming: boolean;
  notesCount: number;
  sendMessage: (query: string, settings: ChatSettings) => Promise<void>;
  clearMessages: () => void;
  loadNotesCount: () => Promise<void>;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isStreaming: false,
  notesCount: 0,

  async loadNotesCount() {
    try {
      const res = await fetch('/api/notes/count');
      const data = await res.json();
      if (data.success) set({ notesCount: data.count });
    } catch {
      // 실패 시 0 유지
    }
  },

  async sendMessage(query, settings) {
    const { messages } = get();

    // API 전송용 — UI 전용 필드 제거
    const apiHistory: ApiMessage[] = messages
      .map(({ role, content }) => ({ role, content }))
      .slice(-15);

    const assistantId = crypto.randomUUID();

    set({
      isStreaming: true,
      messages: [
        ...messages,
        { id: crypto.randomUUID(), role: 'user', content: query },
        {
          id: assistantId,
          role: 'assistant',
          content: '',
          model: settings.model,
          responseLanguage: settings.responseLanguage,
          streaming: true,
        },
      ],
    });

    let accumulated = '';

    try {
      for await (const event of streamSSE('/api/search/stream', {
        query,
        history: apiHistory,
        top_k: settings.topK,
        ignore_token_limit: settings.ignoreTokenLimit,
        model: settings.model,
        response_language: settings.responseLanguage,
      })) {
        set((s) => ({
          messages: s.messages.map((m) => {
            if (m.id !== assistantId) return m;
            if (event.type === 'token') {
              accumulated += event.content as string;
              return { ...m, content: accumulated };
            }
            if (event.type === 'sources') {
              return { ...m, sources: event.sources as Source[] };
            }
            if (event.type === 'done') {
              return {
                ...m,
                streaming: false,
                usage: event.usage as TokenUsage,
                elapsedTime: event.elapsed_time as number,
                cached: event.cached as boolean,
                model: settings.model,
                responseLanguage: settings.responseLanguage,
              };
            }
            return m;
          }),
        }));
      }
    } catch (err) {
      set((s) => ({
        messages: s.messages.map((m) =>
          m.id === assistantId
            ? { ...m, content: `오류가 발생했습니다: ${(err as Error).message}`, streaming: false }
            : m,
        ),
      }));
    } finally {
      set({ isStreaming: false });
    }
  },

  clearMessages: () => set({ messages: [] }),
}));
