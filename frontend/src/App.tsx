import { useEffect, useState } from 'react';
import { useChatStore } from './hooks/useChat';
import { MessageList } from './components/MessageList';
import { ChatInput } from './components/ChatInput';
import { SettingsBar } from './components/SettingsBar';
import type { ChatSettings } from './types';

const DEFAULT_SETTINGS: ChatSettings = {
  topK: 5,
  ignoreTokenLimit: false,
  model: 'gpt-4o-mini',
};

export default function App() {
  const { messages, isStreaming, notesCount, sendMessage, clearMessages, loadNotesCount } = useChatStore();
  const [settings, setSettings] = useState<ChatSettings>(DEFAULT_SETTINGS);

  useEffect(() => {
    loadNotesCount();
  }, [loadNotesCount]);

  const handleClear = () => {
    if (messages.length === 0) return;
    if (confirm('대화 내역을 모두 삭제하시겠습니까?')) clearMessages();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-50 to-purple-100 dark:from-gray-950 dark:to-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-3xl h-[calc(100vh-2rem)] flex flex-col rounded-2xl shadow-2xl overflow-hidden bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700">
        {/* 헤더 */}
        <div className="flex items-center gap-3 px-5 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-purple-700 flex items-center justify-center text-white text-sm font-bold">
            🧠
          </div>
          <div>
            <h1 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Obsidian RAG Chat</h1>
            {notesCount > 0 && (
              <p className="text-xs text-gray-400">{notesCount}개 노트 검색 가능</p>
            )}
          </div>
        </div>

        {/* 메시지 목록 */}
        <MessageList messages={messages} />

        {/* 설정 바 */}
        <SettingsBar
          settings={settings}
          onChange={setSettings}
          notesCount={notesCount}
          onClear={handleClear}
        />

        {/* 입력 */}
        <ChatInput onSend={(text) => sendMessage(text, settings)} disabled={isStreaming} />
      </div>
    </div>
  );
}
