import type { ChatSettings } from '../types';

interface Props {
  settings: ChatSettings;
  onChange: (s: ChatSettings) => void;
  notesCount: number;
  onClear: () => void;
}

const MODELS = [
  { value: 'gpt-4o-mini', label: 'GPT-4o-mini (빠름)' },
  { value: 'gpt-5-mini', label: 'GPT-5-mini (고성능)' },
];

export function SettingsBar({ settings, onChange, notesCount, onClear }: Props) {
  const topKLabel = () => {
    if (settings.topK <= 5) return '⚡ 권장';
    if (settings.topK <= 20) return '보통';
    if (settings.topK <= 50) return '⏳ 느림';
    return '🐌 매우 느림';
  };

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-xs text-gray-600 dark:text-gray-400">
      {/* 노트 수 */}
      {notesCount > 0 && (
        <span className="text-violet-600 dark:text-violet-400 font-medium">
          📁 {notesCount}개 노트
        </span>
      )}

      {/* top_k */}
      <label className="flex items-center gap-1.5">
        <span>검색 노트 수</span>
        <input
          type="number"
          min={1}
          max={notesCount || 999}
          value={settings.topK}
          onChange={(e) => onChange({ ...settings, topK: Number(e.target.value) })}
          className="w-14 px-1.5 py-0.5 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-center"
        />
        <span className="text-gray-400">{topKLabel()}</span>
      </label>

      {/* 모델 */}
      <label className="flex items-center gap-1.5">
        <span>모델</span>
        <select
          value={settings.model}
          onChange={(e) => onChange({ ...settings, model: e.target.value })}
          className="px-1.5 py-0.5 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
        >
          {MODELS.map((m) => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
        {settings.model === 'gpt-5-mini' && (
          <span className="text-amber-500 text-xs">스트리밍 미지원</span>
        )}
      </label>

      {/* 최대 토큰 모드 */}
      <label className="flex items-center gap-1.5 cursor-pointer">
        <input
          type="checkbox"
          checked={settings.ignoreTokenLimit}
          onChange={(e) => onChange({ ...settings, ignoreTokenLimit: e.target.checked })}
          className="accent-violet-500"
        />
        <span>최대 토큰 모드</span>
      </label>

      {/* 대화 초기화 */}
      <button
        onClick={onClear}
        className="ml-auto px-3 py-1 rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
      >
        대화 초기화
      </button>
    </div>
  );
}
