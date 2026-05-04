import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';
import type { Message } from '../types';
import { SourceList } from './SourceList';
import { UsageBadge } from './UsageBadge';

interface Props {
  message: Message;
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* 아바타 */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-base shrink-0 ${
        isUser
          ? 'bg-gradient-to-br from-violet-500 to-purple-700'
          : 'bg-gray-200 dark:bg-gray-700'
      }`}>
        {isUser ? '👤' : '🤖'}
      </div>

      {/* 내용 */}
      <div className={`flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'} max-w-[80%]`}>
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? 'bg-gradient-to-br from-violet-500 to-purple-700 text-white rounded-tr-sm'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-tl-sm'
        }`}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none
              prose-headings:font-semibold prose-headings:mt-3 prose-headings:mb-1
              prose-p:my-1 prose-li:my-0.5
              prose-code:bg-black/10 dark:prose-code:bg-white/10 prose-code:px-1 prose-code:rounded prose-code:text-xs prose-code:before:content-none prose-code:after:content-none
              prose-pre:bg-gray-900 prose-pre:rounded-lg prose-pre:p-0 prose-pre:overflow-hidden">
              <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
                {message.content}
              </ReactMarkdown>
              {message.streaming && (
                <span className="inline-block w-0.5 h-4 bg-gray-600 dark:bg-gray-300 animate-pulse align-middle ml-0.5" />
              )}
            </div>
          )}
        </div>

        {!isUser && message.sources && message.sources.length > 0 && (
          <SourceList sources={message.sources} />
        )}

        {!isUser && !message.streaming && message.usage && (
          <UsageBadge usage={message.usage} elapsed={message.elapsedTime} cached={message.cached} />
        )}
      </div>
    </div>
  );
}
