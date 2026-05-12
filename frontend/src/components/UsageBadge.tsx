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

const COPY = {
  auto: {
    cached: '캐시됨',
    seconds: (value: string) => `${value}초`,
    tokens: (value: string) => `${value} 토큰`,
    inputOutput: (input: string, output: string) => `입력 ${input} · 출력 ${output}`,
  },
  ko: {
    cached: '캐시됨',
    seconds: (value: string) => `${value}초`,
    tokens: (value: string) => `${value} 토큰`,
    inputOutput: (input: string, output: string) => `입력 ${input} · 출력 ${output}`,
  },
  en: {
    cached: 'Cached',
    seconds: (value: string) => `${value}s`,
    tokens: (value: string) => `${value} tokens`,
    inputOutput: (input: string, output: string) => `Input ${input} · Output ${output}`,
  },
  ja: {
    cached: 'キャッシュ',
    seconds: (value: string) => `${value}秒`,
    tokens: (value: string) => `${value} トークン`,
    inputOutput: (input: string, output: string) => `入力 ${input} · 出力 ${output}`,
  },
} satisfies Record<ResponseLanguage, {
  cached: string;
  seconds: (value: string) => string;
  tokens: (value: string) => string;
  inputOutput: (input: string, output: string) => string;
}>;

export function UsageBadge({ usage, elapsed, cached, model, responseLanguage }: Props) {
  const isCached = cached || usage.total_tokens === 0;
  const language = responseLanguage ?? 'auto';
  const copy = COPY[language];
  const elapsedLabel = typeof elapsed === 'number' ? copy.seconds(elapsed.toFixed(isCached ? 3 : 2)) : null;

  return (
    <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
      {isCached ? (
        <span className="rounded-md bg-green-50 px-2.5 py-1 font-medium text-green-700 dark:bg-green-950/30 dark:text-green-400">
          {copy.cached}
        </span>
      ) : (
        <span className="rounded-md bg-gray-100 px-2.5 py-1 dark:bg-gray-800">
          {copy.tokens(usage.total_tokens.toLocaleString())}
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
          {LANGUAGE_LABELS[language]}
        </span>
      )}
      {!isCached && (
        <span className="rounded-md bg-gray-100 px-2.5 py-1 opacity-80 dark:bg-gray-800">
          {copy.inputOutput(
            usage.prompt_tokens.toLocaleString(),
            usage.completion_tokens.toLocaleString(),
          )}
        </span>
      )}
    </div>
  );
}
