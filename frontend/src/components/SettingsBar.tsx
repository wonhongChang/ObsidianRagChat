import type { ChatModel, ChatSettings, ResponseLanguage } from '../types';

interface Props {
  settings: ChatSettings;
  onChange: (s: ChatSettings) => void;
  notesCount: number;
  onClear: () => void;
  canClear: boolean;
}

const MODELS = [
  { value: 'gpt-4o-mini', label: 'GPT-4o-mini' },
  { value: 'gpt-5-mini', label: 'GPT-5-mini' },
] satisfies Array<{ value: ChatModel; label: string }>;

const LANGUAGES = [
  { value: 'auto', label: 'Auto' },
  { value: 'ko', label: '한국어' },
  { value: 'en', label: 'English' },
  { value: 'ja', label: '日本語' },
] satisfies Array<{ value: ResponseLanguage; label: string }>;

const COPY = {
  auto: {
    notes: (count: number) => `${count}개 노트`,
    topK: '참조 노트 수',
    recommended: '권장 5개',
    normal: '보통',
    slow: '느림',
    responseLanguage: '응답 언어',
    maxToken: '최대 토큰 모드',
    clear: '대화 초기화',
    noStreaming: '스트리밍 미지원',
  },
  ko: {
    notes: (count: number) => `${count}개 노트`,
    topK: '참조 노트 수',
    recommended: '권장 5개',
    normal: '보통',
    slow: '느림',
    responseLanguage: '응답 언어',
    maxToken: '최대 토큰 모드',
    clear: '대화 초기화',
    noStreaming: '스트리밍 미지원',
  },
  en: {
    notes: (count: number) => `${count} notes`,
    topK: 'Sources',
    recommended: 'Rec 5',
    normal: 'Normal',
    slow: 'Slow',
    responseLanguage: 'Lang',
    maxToken: 'Max tokens',
    clear: 'Clear',
    noStreaming: 'No stream',
  },
  ja: {
    notes: (count: number) => `${count}件のノート`,
    topK: '参照',
    recommended: 'おすすめ 5件',
    normal: '通常',
    slow: '遅め',
    responseLanguage: '言語',
    maxToken: '最大トークン',
    clear: 'クリア',
    noStreaming: '非ストリーム',
  },
} satisfies Record<ResponseLanguage, {
  notes: (count: number) => string;
  topK: string;
  recommended: string;
  normal: string;
  slow: string;
  responseLanguage: string;
  maxToken: string;
  clear: string;
  noStreaming: string;
}>;

export function SettingsBar({ settings, onChange, notesCount, onClear, canClear }: Props) {
  const maxTopK = Math.min(notesCount || 50, 50);
  const copy = COPY[settings.responseLanguage];

  const topKLabel = () => {
    if (settings.topK <= 5) return copy.recommended;
    if (settings.topK <= 20) return copy.normal;
    return copy.slow;
  };

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-y-1.5 sm:gap-y-0 sm:gap-x-3 px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-xs text-gray-600 dark:text-gray-400">
      {/* 그룹1: 노트 수 + 검색 노트 수 */}
      <div className="flex items-center gap-2.5">
        {notesCount > 0 && (
          <span className="text-violet-600 dark:text-violet-400 font-medium whitespace-nowrap">
            {copy.notes(notesCount)}
          </span>
        )}
        <label className="flex items-center gap-1.5">
          <span className="whitespace-nowrap">{copy.topK}</span>
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
      <div className="flex flex-wrap items-center gap-2.5 sm:ml-auto">
        <label className="flex items-center gap-1.5">
          <span className="whitespace-nowrap">{copy.responseLanguage}</span>
          <select
            aria-label="응답 언어"
            value={settings.responseLanguage}
            onChange={(e) => onChange({ ...settings, responseLanguage: e.target.value as ResponseLanguage })}
            className="px-1.5 py-0.5 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
          >
            {LANGUAGES.map((language) => (
              <option key={language.value} value={language.value}>{language.label}</option>
            ))}
          </select>
        </label>
        <div className="flex items-center gap-1.5">
          <select
            aria-label="모델"
            value={settings.model}
            onChange={(e) => onChange({ ...settings, model: e.target.value as ChatModel })}
            className="px-1.5 py-0.5 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
          >
            {MODELS.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
          {settings.model === 'gpt-5-mini' && (
            <span className="whitespace-nowrap text-amber-500">{copy.noStreaming}</span>
          )}
        </div>
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.ignoreTokenLimit}
            onChange={(e) => onChange({ ...settings, ignoreTokenLimit: e.target.checked })}
            className="accent-violet-500"
          />
          <span className="whitespace-nowrap">{copy.maxToken}</span>
        </label>
        {canClear && (
          <button
            onClick={onClear}
            className="ml-auto sm:ml-0 px-2.5 py-1 rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors whitespace-nowrap"
          >
            {copy.clear}
          </button>
        )}
      </div>
    </div>
  );
}
