import { useState } from 'react';
import type { ResponseLanguage, Source } from '../types';

interface Props {
  sources: Source[];
  responseLanguage: ResponseLanguage;
}

const COPY = {
  auto: { sources: (count: number) => `출처 ${count}개`, average: '평균' },
  ko: { sources: (count: number) => `출처 ${count}개`, average: '평균' },
  en: { sources: (count: number) => `${count} sources`, average: 'avg' },
  ja: { sources: (count: number) => `出典 ${count}件`, average: '平均' },
} satisfies Record<ResponseLanguage, {
  sources: (count: number) => string;
  average: string;
}>;

export function SourceList({ sources, responseLanguage }: Props) {
  const [open, setOpen] = useState(false);
  const averageScore = sources.reduce((sum, src) => sum + src.score, 0) / sources.length;
  const copy = COPY[responseLanguage];

  return (
    <div className="mt-2 w-full rounded-lg border border-violet-200 bg-violet-50 text-sm dark:border-violet-900 dark:bg-violet-950/30">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-violet-700 transition-colors hover:bg-violet-100 dark:text-violet-300 dark:hover:bg-violet-900/30"
      >
        <span className="text-xs transition-transform duration-200" style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}>▼</span>
        <span className="font-medium">{copy.sources(sources.length)}</span>
        <span className="ml-auto text-xs opacity-70">{copy.average} {(averageScore * 100).toFixed(1)}%</span>
      </button>

      {open && (
        <div className="px-3 pb-3 flex flex-col gap-2">
          {sources.map((src, i) => (
            <div key={`${src.filename}-${i}`} className="rounded-md border-l-4 border-violet-500 bg-white px-3 py-2 dark:bg-gray-800">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate font-medium text-gray-800 dark:text-gray-200">
                    {src.filename}
                  </div>
                  {src.section && (
                    <div className="mt-0.5 truncate text-xs text-gray-500 dark:text-gray-400">
                      {src.section}
                    </div>
                  )}
                </div>
                <span className="shrink-0 text-xs text-gray-400">
                  {(src.score * 100).toFixed(1)}%
                </span>
              </div>
              {src.tags && src.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {src.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 rounded-full bg-violet-100 dark:bg-violet-900 text-violet-700 dark:text-violet-300 text-xs"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              )}
              {src.text && (
                <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">
                  {src.text}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
