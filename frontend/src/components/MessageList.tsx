import { useEffect, useRef } from 'react';
import type { Message, ResponseLanguage } from '../types';
import { ChatMessage } from './ChatMessage';

interface Props {
  messages: Message[];
  onPromptSelect: (text: string) => void;
  disabled: boolean;
  responseLanguage: ResponseLanguage;
}

const DEMO_PROMPTS: Record<ResponseLanguage, Array<{ label: string; prompt: string }>> = {
  auto: [
    { label: '한국어', prompt: '#DemoRAG 이 프로젝트를 포트폴리오 관점에서 요약해줘' },
    { label: 'English', prompt: '#DemoRAG Summarize this project for a portfolio.' },
    { label: '日本語', prompt: '#DemoRAG このプロジェクトの同期とキャッシュ戦略を説明して' },
    { label: 'Cache', prompt: '#DemoRAG 프론트엔드에서 개선하면 좋은 점을 알려줘' },
  ],
  ko: [
    { label: '요약', prompt: '#DemoRAG 이 프로젝트를 포트폴리오 관점에서 요약해줘' },
    { label: '아키텍처', prompt: '#DemoRAG 동기화와 캐싱 구조를 설명해줘' },
    { label: '데모', prompt: '#DemoRAG 태그 검색과 캐시 히트를 보여줄 질문을 추천해줘' },
    { label: '개선', prompt: '#DemoRAG 프론트엔드에서 개선하면 좋은 점을 알려줘' },
  ],
  en: [
    { label: 'Summary', prompt: '#DemoRAG Summarize this project for a portfolio.' },
    { label: 'Architecture', prompt: '#DemoRAG Explain the sync and caching architecture.' },
    { label: 'Demo', prompt: '#DemoRAG Suggest questions that show tag search and cache hits.' },
    { label: 'Polish', prompt: '#DemoRAG What frontend improvements would make the demo stronger?' },
  ],
  ja: [
    { label: '要約', prompt: '#DemoRAG このプロジェクトをポートフォリオ向けに要約して' },
    { label: '構成', prompt: '#DemoRAG このプロジェクトの同期とキャッシュ戦略を説明して' },
    { label: 'デモ', prompt: '#DemoRAG タグ検索とキャッシュヒットを見せる質問を提案して' },
    { label: '改善', prompt: '#DemoRAG フロントエンドで改善すると良い点を教えて' },
  ],
};

export function MessageList({ messages, onPromptSelect, disabled, responseLanguage }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const prompts = DEMO_PROMPTS[responseLanguage];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-5 text-center p-8">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-700 flex items-center justify-center text-white text-2xl shadow-lg shadow-violet-500/20">
          ◈
        </div>
        <div>
          <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">Obsidian RAG Chat</h2>
          <div className="mt-2 flex items-center justify-center gap-2 text-xs text-gray-400">
            <span className="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800">#DemoRAG</span>
            <span className="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800">Multilingual</span>
            <span className="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800">Qdrant</span>
            <span className="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800">Redis</span>
          </div>
        </div>
        <div className="grid w-full max-w-xl grid-cols-1 gap-2 sm:grid-cols-2">
          {prompts.map((item) => (
            <button
              key={item.prompt}
              type="button"
              disabled={disabled}
              onClick={() => onPromptSelect(item.prompt)}
              className="group min-h-20 rounded-lg border border-gray-200 bg-white px-4 py-3 text-left text-sm text-gray-700 shadow-sm transition hover:border-violet-300 hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:border-violet-700 dark:hover:bg-violet-950/30"
            >
              <span className="mb-1 block text-xs font-medium text-violet-600 dark:text-violet-300">
                {item.label}
              </span>
              <span className="line-clamp-2 leading-relaxed">{item.prompt}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4">
      {messages.map((msg) => (
        <ChatMessage key={msg.id} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
