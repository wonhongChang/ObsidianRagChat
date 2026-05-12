import type { ChatModel, ResponseLanguage, TokenUsage } from '../types';

interface Props {
  usage: TokenUsage;
  elapsed?: number;
  cached?: boolean;
  model?: ChatModel;
  responseLanguage?: ResponseLanguage;
}

const LANGUAGE_LABELS: Record<ResponseLanguage, string> = {
  auto: 'Auto language',
  ko: '한국어',
  en: 'English',
  ja: '日本語',
};

export function UsageBadge({ usage, elapsed, cached, model, responseLanguage }: Props) {
  const isCached = cached || usage.total_tokens === 0;
  const elapsedLabel = typeof elapsed === 'number' ? `${elapsed.toFixed(isCached ? 3 : 2)}초` : null;

  return (
    <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
      {isCached ? (
        <span className="rounded-md bg-green-50 px-2.5 py-1 font-medium text-green-700 dark:bg-green-950/30 dark:text-green-400">
          캐시됨
        </span>
      ) : (
        <span className="rounded-md bg-gray-100 px-2.5 py-1 dark:bg-gray-800">
          {usage.total_tokens.toLocaleString()} 토큰
        </span>
      )}
      {elapsedLabel && (
        <span className="rounded-md bg-gray-100 px-2.5 py-1 dark:bg-gray-800">
          {elapsedLabel}
        </span>
      )}
      {model && (
        <span className="rounded-md bg-gray-100 px-2.5 py-1 dark:bg-gray-800">
          {model}
        </span>
      )}
      {responseLanguage && (
        <span className="rounded-md bg-gray-100 px-2.5 py-1 dark:bg-gray-800">
          {LANGUAGE_LABELS[responseLanguage]}
        </span>
      )}
      {!isCached && (
        <span className="rounded-md bg-gray-100 px-2.5 py-1 opacity-80 dark:bg-gray-800">
          입력 {usage.prompt_tokens.toLocaleString()} · 출력 {usage.completion_tokens.toLocaleString()}
        </span>
      )}
    </div>
  );
}
