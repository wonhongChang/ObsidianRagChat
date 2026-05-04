import { useEffect, useRef } from 'react';
import type { Message } from '../types';
import { ChatMessage } from './ChatMessage';

interface Props {
  messages: Message[];
}

export function MessageList({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center p-8">
        <div className="text-5xl">🧠</div>
        <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-300">Obsidian RAG Chat</h2>
        <p className="text-gray-500 dark:text-gray-400 text-sm max-w-sm">
          질문을 입력하면 노트를 벡터 검색해 GPT가 답변합니다.
        </p>
        <div className="flex flex-wrap gap-2 justify-center mt-2">
          {[
            '와인 추천해줘',
            '#interview 태그 문서 요약',
            '자기소개서 어떻게 써?',
          ].map((hint) => (
            <span
              key={hint}
              className="px-3 py-1 rounded-full bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300 text-xs"
            >
              {hint}
            </span>
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
