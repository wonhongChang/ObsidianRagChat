import type { TokenUsage } from '../types';

interface Props {
  usage: TokenUsage;
  elapsed?: number;
  cached?: boolean;
}

export function UsageBadge({ usage, elapsed, cached }: Props) {
  const isCached = cached || usage.total_tokens === 0;

  return (
    <div className={`text-xs px-3 py-1.5 rounded-md mt-1 ${
      isCached
        ? 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-400'
        : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400'
    }`}>
      {isCached ? (
        <>⚡ 캐시된 응답 · {elapsed?.toFixed(3)}초</>
      ) : (
        <>
          💰 {usage.total_tokens.toLocaleString()} 토큰
          <span className="opacity-60 ml-1">
            (입력 {usage.prompt_tokens.toLocaleString()} + 출력 {usage.completion_tokens.toLocaleString()})
          </span>
          {elapsed && <> · ⏱️ {elapsed.toFixed(2)}초</>}
        </>
      )}
    </div>
  );
}
