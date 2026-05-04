import { useRef, useEffect } from 'react';

interface Props {
  onSend: (text: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!disabled) ref.current?.focus();
  }, [disabled]);

  const resize = () => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const submit = () => {
    const text = ref.current?.value.trim();
    if (!text || disabled) return;
    onSend(text);
    ref.current!.value = '';
    ref.current!.style.height = 'auto';
  };

  return (
    <div className="flex items-end gap-2 px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
      <textarea
        ref={ref}
        rows={1}
        disabled={disabled}
        placeholder="질문을 입력하세요…"
        className="flex-1 resize-none rounded-2xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 px-4 py-2.5 text-sm leading-relaxed outline-none focus:border-violet-500 dark:focus:border-violet-400 transition-colors disabled:opacity-50"
        onInput={resize}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
      />
      <button
        onClick={submit}
        disabled={disabled}
        className="w-10 h-10 rounded-full bg-gradient-to-br from-violet-500 to-purple-700 text-white flex items-center justify-center shrink-0 hover:opacity-90 active:scale-95 transition disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {disabled ? (
          <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
        ) : (
          <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 translate-x-0.5">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        )}
      </button>
    </div>
  );
}
