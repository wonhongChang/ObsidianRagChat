import { useState } from 'react';
import type { Source } from '../types';

interface Props {
  sources: Source[];
}

export function SourceList({ sources }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-2 rounded-lg border border-violet-200 dark:border-violet-900 bg-violet-50 dark:bg-violet-950/30 text-sm">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 text-violet-700 dark:text-violet-300 font-medium hover:bg-violet-100 dark:hover:bg-violet-900/30 rounded-lg transition-colors"
      >
        <span className="transition-transform duration-200" style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}>▼</span>
        <span>📚 참조한 노트 ({sources.length}개)</span>
      </button>

      {open && (
        <div className="px-3 pb-3 flex flex-col gap-2">
          {sources.map((src, i) => (
            <div key={i} className="bg-white dark:bg-gray-800 rounded-md px-3 py-2 border-l-4 border-violet-500">
              <div className="font-medium text-gray-800 dark:text-gray-200">
                📄 {src.filename}
                <span className="ml-2 text-xs text-gray-400">
                  유사도 {(src.score * 100).toFixed(1)}%
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
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
