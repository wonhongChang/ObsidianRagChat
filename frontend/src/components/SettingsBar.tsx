import type { ChatModel, ChatSettings } from '../types';

interface Props {
  settings: ChatSettings;
  onChange: (s: ChatSettings) => void;
  notesCount: number;
  onClear: () => void;
}

const MODELS = [
  { value: 'gpt-4o-mini', label: 'GPT-4o-mini' },
  { value: 'gpt-5-mini', label: 'GPT-5-mini' },
] satisfies Array<{ value: ChatModel; label: string }>;

export function SettingsBar({ settings, onChange, notesCount, onClear }: Props) {
  const maxTopK = Math.min(notesCount || 50, 50);

  const topKLabel = () => {
    if (settings.topK < 5) return '↑ 권장 5개';
    if (settings.topK === 5) return '⚡ 권장 5개';
    if (settings.topK <= 20) return '보통';
    if (settings.topK <= 50) return '⏳ 느림';
    return '🐌 매우 느림';
  };

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-y-1.5 sm:gap-y-0 sm:gap-x-4 px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-xs text-gray-600 dark:text-gray-400">
      {/* 그룹1: 노트 수 + 검색 노트 수 */}
      <div className="flex items-center gap-3">
        {notesCount > 0 && (
          <span className="text-violet-600 dark:text-violet-400 font-medium whitespace-nowrap">
            📁 {notesCount}개 노트
          </span>
        )}
        <label className="flex items-center gap-1.5">
          <span className="whitespace-nowrap">참조 노트 수</span>
          <input
            type="number"
            min={1}
            max={maxTopK}
            value={settings.topK}
            onChange={(e) => {
              const value = Number(e.target.value);
              const topK = Number.isFinite(value) ? Math.min(Math.max(value, 1), maxTopK) : 5;
              onChange({ ...settings, topK });
            }}
            className="w-14 px-1.5 py-0.5 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-center"
          />
          <span className={`whitespace-nowrap ${
            settings.topK === 5 ? 'text-green-500 dark:text-green-400' :
            settings.topK < 5 ? 'text-amber-500 dark:text-amber-400' :
            settings.topK <= 20 ? 'text-gray-400' :
            'text-red-500 dark:text-red-400'
          }`}>{topKLabel()}</span>
        </label>
      </div>

      {/* 그룹2: 모델 + 최대 토큰 모드 + 대화 초기화 */}
      <div className="flex items-center gap-3 sm:ml-auto">
        <div className="flex items-center gap-1.5">
          <select
            value={settings.model}
            onChange={(e) => onChange({ ...settings, model: e.target.value as ChatModel })}
            className="px-1.5 py-0.5 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
          >
            {MODELS.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
          {settings.model === 'gpt-5-mini' && (
            <span className="whitespace-nowrap text-amber-500">스트리밍 미지원</span>
          )}
        </div>
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.ignoreTokenLimit}
            onChange={(e) => onChange({ ...settings, ignoreTokenLimit: e.target.checked })}
            className="accent-violet-500"
          />
          <span className="whitespace-nowrap">최대 토큰 모드</span>
        </label>
        <button
          onClick={onClear}
          className="ml-auto sm:ml-0 px-3 py-1 rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors whitespace-nowrap"
        >
          대화 초기화
        </button>
      </div>
    </div>
  );
}
