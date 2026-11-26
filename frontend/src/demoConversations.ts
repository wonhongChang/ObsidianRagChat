import type { Message, ResponseLanguage, Source, TokenUsage } from './types';

const SOURCES: Source[] = [
  {
    filename: '01_Architecture.md',
    section: 'Multilingual RAG flow',
    score: 0.94,
    tags: ['DemoRAG', 'Architecture'],
    text: 'FastAPI routes the request through Redis, Qdrant, Elasticsearch, and the answer generation layer.',
  },
  {
    filename: '02_Sync_Cache_Search.md',
    section: 'Cache key design',
    score: 0.91,
    tags: ['DemoRAG', 'Cache'],
    text: 'The cache key includes normalized query, top_k, model, response language, and follow-up history hash.',
  },
];

const TAG_SOURCES: Source[] = [
  {
    filename: '00_Demo_Index.md',
    section: '#DemoRAG index',
    score: 0.97,
    tags: ['DemoRAG', 'Index'],
    text: 'Demo notes are grouped by #DemoRAG so tag-filtered retrieval can narrow the search scope before vector ranking.',
  },
  {
    filename: '02_Sync_Cache_Search.md',
    section: 'Tag and search flow',
    score: 0.93,
    tags: ['DemoRAG', 'Search'],
    text: 'Elasticsearch filters matching note paths, then Qdrant ranks relevant chunks inside the filtered set.',
  },
];

const FOLLOWUP_SOURCES: Source[] = [
  {
    filename: '03_Followup_and_Quality.md',
    section: 'Follow-up handling',
    score: 0.95,
    tags: ['DemoRAG', 'Followup'],
    text: 'Follow-up questions keep recent conversation context and rewrite ambiguous questions into standalone retrieval queries.',
  },
  {
    filename: '02_Sync_Cache_Search.md',
    section: 'History-aware cache key',
    score: 0.9,
    tags: ['DemoRAG', 'Cache'],
    text: 'The cache key includes history hash only when the question depends on previous conversation context.',
  },
];

const USAGE: TokenUsage = {
  prompt_tokens: 1248,
  completion_tokens: 284,
  total_tokens: 1532,
};

const ANSWERS: Record<Exclude<ResponseLanguage, 'auto'>, { query: string; answer: string }> = {
  ko: {
    query: '#DemoRAG 이 프로젝트를 포트폴리오 관점에서 요약해줘',
    answer: `이 프로젝트는 Obsidian vault를 검색 가능한 개인 지식 RAG로 바꾸는 웹 앱입니다. Markdown 노트를 주기적으로 동기화하고, Qdrant 벡터 검색과 Elasticsearch 태그 필터를 함께 사용해 관련 문서를 찾습니다. Redis는 동일 질문과 언어별 답변을 캐싱해 반복 질문의 응답 시간과 API 비용을 줄입니다. [노트 1][노트 2]

포트폴리오 관점에서는 단순 챗봇보다 강점이 분명합니다. Docker Compose로 전체 서비스를 재현할 수 있고, follow-up 질문과 독립 질문을 구분하며, 한국어/영어/일본어 응답 언어도 캐시 키에 반영합니다. [노트 1]`,
  },
  en: {
    query: '#DemoRAG Summarize this project for a portfolio.',
    answer: `Obsidian RAG Chat turns a private Obsidian vault into a searchable multilingual RAG application. It syncs Markdown notes, chunks them by heading, stores semantic vectors in Qdrant, and narrows tag-specific searches with Elasticsearch. Redis caches repeated questions, including the selected response language, so repeat queries return quickly without another model call. [Note 1][Note 2]

For a portfolio, the project demonstrates practical backend architecture rather than a thin chat wrapper: Dockerized services, streaming responses, follow-up handling, cache-aware retrieval, and multilingual answer control. [Note 1]`,
  },
  ja: {
    query: '#DemoRAG このプロジェクトをポートフォリオ向けに要約して',
    answer: `Obsidian RAG Chat は、Obsidian vault を多言語対応の RAG アプリケーションに変換するプロジェクトです。Markdown ノートを同期し、見出し単位でチャンク化して Qdrant にベクトル保存し、タグ検索では Elasticsearch で候補を絞り込みます。Redis は同じ質問と回答言語を含めてキャッシュするため、再質問時の応答速度と API コストを抑えられます。[ノート 1][ノート 2]

ポートフォリオとしては、単なるチャット UI ではなく、Docker 化された複数サービス、ストリーミング応答、フォローアップ処理、キャッシュ設計、多言語回答制御まで説明できる点が強みです。[ノート 1]`,
  },
};

const TAG_ANSWERS: Record<Exclude<ResponseLanguage, 'auto'>, { query: string; answer: string }> = {
  ko: {
    query: '#DemoRAG 태그 문서를 기준으로 검색 구조를 설명해줘',
    answer: `#DemoRAG 태그가 포함된 문서만 먼저 좁힌 뒤, 그 안에서 Qdrant 벡터 검색으로 관련 청크를 다시 랭킹합니다. 태그 필터는 Elasticsearch가 담당하고, 의미 유사도 정렬은 Qdrant가 담당하므로 “범위 제한”과 “의미 검색”을 분리한 구조입니다. [노트 1][노트 2]

이 방식은 데모에서 특히 좋습니다. 특정 주제 태그를 입력하면 무관한 개인 노트가 검색 후보에서 빠지고, 답변 출처도 같은 태그 문서로 모여 리뷰어가 검색 근거를 확인하기 쉽습니다. [노트 2]`,
  },
  en: {
    query: '#DemoRAG Explain the retrieval flow using the tagged demo notes.',
    answer: `When a query includes #DemoRAG, Elasticsearch first narrows the candidate note paths to documents carrying that tag. Qdrant then performs semantic chunk ranking only inside that filtered set, so the system combines exact tag scope with vector relevance. [Note 1][Note 2]

That separation makes the demo easier to trust: reviewers can see that tagged notes constrain the search space, while the vector layer still chooses the most relevant chunks for answer generation. [Note 2]`,
  },
  ja: {
    query: '#DemoRAG タグ付きノートを使った検索フローを説明して',
    answer: `#DemoRAG を含む質問では、まず Elasticsearch がそのタグを持つノートのパスに候補を絞り込みます。その後、Qdrant が絞り込まれた範囲の中でチャンクを意味検索し、関連度順に並べます。[ノート 1][ノート 2]

この分離により、タグで検索範囲を明確に制限しつつ、回答生成には意味的に近いチャンクを使えます。デモでは、出典が同じタグのノートに集まるため、検索根拠も確認しやすくなります。[ノート 2]`,
  },
};

const FOLLOWUP_ANSWERS: Record<Exclude<ResponseLanguage, 'auto'>, {
  firstQuery: string;
  firstAnswer: string;
  followupQuery: string;
  followupAnswer: string;
}> = {
  ko: {
    firstQuery: '#DemoRAG 이 프로젝트의 캐싱 전략을 설명해줘',
    firstAnswer: `이 프로젝트는 Redis를 사용해 RAG 응답을 캐싱합니다. 캐시 키에는 정규화된 질문, top_k, 모델, 응답 언어가 들어가고, 이전 대화에 의존하는 질문일 때만 history hash가 추가됩니다. [노트 1]`,
    followupQuery: '그럼 이전 질문이 필요한 경우는 어떻게 구분해?',
    followupAnswer: `후속 질문은 먼저 규칙 기반으로 독립 질문인지 판단합니다. “그럼”, “이 경우”, “방금 말한 것”처럼 이전 답변을 참조하는 질문이면 최근 대화 맥락을 포함해 standalone 검색 쿼리로 재작성한 뒤 검색합니다. 반대로 새 주제나 명확한 태그 질문이면 history를 제외해 캐시 재사용성이 높아집니다. [노트 1][노트 2]`,
  },
  en: {
    firstQuery: '#DemoRAG Explain the caching strategy in this project.',
    firstAnswer: `The app caches RAG answers in Redis. The key includes the normalized query, top_k, model, and response language. A history hash is added only when the question depends on previous conversation context. [Note 1]`,
    followupQuery: 'How does it know when the previous question is needed?',
    followupAnswer: `The backend first classifies the new message as standalone or follow-up. If the wording depends on prior context, the recent conversation is used to rewrite it into a standalone retrieval query. If the question is clearly independent, history is excluded so repeated standalone questions can hit the same cache entry. [Note 1][Note 2]`,
  },
  ja: {
    firstQuery: '#DemoRAG このプロジェクトのキャッシュ戦略を説明して',
    firstAnswer: `このアプリは Redis に RAG 応答をキャッシュします。キーには正規化した質問、top_k、モデル、回答言語が入り、前の会話に依存する質問の場合だけ history hash を追加します。[ノート 1]`,
    followupQuery: '前の質問が必要かどうかはどう判断するの？',
    followupAnswer: `バックエンドはまず、新しい質問が独立質問かフォローアップかを判定します。前の回答に依存する表現なら、直近の会話を使って standalone な検索クエリに書き換えてから検索します。新しい主題や明確なタグ質問なら history を外し、同じ質問のキャッシュヒットを狙いやすくします。[ノート 1][ノート 2]`,
  },
};

function makeAnswerConversation(language: Exclude<ResponseLanguage, 'auto'>, cached = false): Message[] {
  const item = ANSWERS[language];
  return [
    {
      id: `demo-${language}-user`,
      role: 'user',
      content: item.query,
    },
    {
      id: `demo-${language}-assistant`,
      role: 'assistant',
      content: item.answer,
      sources: SOURCES,
      usage: cached ? { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 } : USAGE,
      elapsedTime: cached ? 0.014 : 2.38,
      cached,
      responseLanguage: language,
      streaming: false,
    },
  ];
}

function makeTagConversation(language: Exclude<ResponseLanguage, 'auto'>): Message[] {
  const item = TAG_ANSWERS[language];
  return [
    {
      id: `demo-${language}-tag-user`,
      role: 'user',
      content: item.query,
    },
    {
      id: `demo-${language}-tag-assistant`,
      role: 'assistant',
      content: item.answer,
      sources: TAG_SOURCES,
      usage: { prompt_tokens: 982, completion_tokens: 246, total_tokens: 1228 },
      elapsedTime: 1.86,
      cached: false,
      responseLanguage: language,
      streaming: false,
    },
  ];
}

function makeFollowupConversation(language: Exclude<ResponseLanguage, 'auto'>): Message[] {
  const item = FOLLOWUP_ANSWERS[language];
  return [
    {
      id: `demo-${language}-followup-first-user`,
      role: 'user',
      content: item.firstQuery,
    },
    {
      id: `demo-${language}-followup-first-assistant`,
      role: 'assistant',
      content: item.firstAnswer,
      sources: FOLLOWUP_SOURCES.slice(0, 1),
      usage: { prompt_tokens: 894, completion_tokens: 128, total_tokens: 1022 },
      elapsedTime: 1.74,
      cached: false,
      responseLanguage: language,
      streaming: false,
    },
    {
      id: `demo-${language}-followup-second-user`,
      role: 'user',
      content: item.followupQuery,
    },
    {
      id: `demo-${language}-followup-second-assistant`,
      role: 'assistant',
      content: item.followupAnswer,
      sources: FOLLOWUP_SOURCES,
      usage: { prompt_tokens: 1326, completion_tokens: 218, total_tokens: 1544 },
      elapsedTime: 2.12,
      cached: false,
      responseLanguage: language,
      streaming: false,
    },
  ];
}

export function getDemoConversation(mode: string | null, language: ResponseLanguage): Message[] | null {
  if (!mode) return null;
  const fixedLanguage = language === 'auto' ? 'en' : language;

  if (mode === 'answer') return makeAnswerConversation(fixedLanguage);
  if (mode === 'tag') return makeTagConversation(fixedLanguage);
  if (mode === 'followup') return makeFollowupConversation(fixedLanguage);
  if (mode === 'cache') return makeAnswerConversation(fixedLanguage, true);

  return null;
}
