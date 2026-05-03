# Obsidian RAG Chat

ObsidianノートをRAGシステムに変換してGPTと対話するWebインターフェース。

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)](https://fastapi.tiangolo.com/)

---

## アーキテクチャ

```
ユーザー質問
    │
    ▼
[app.py] FastAPI :8001
    ├─ ルールベース 独立/フォローアップ判定 (GPT不使用)
    ├─ Redisキャッシュ確認 → ヒット時は即座に返却 (TTL 30分)
    │
    ▼ (ミス時)
[rag/generator.py]
    ├─ フォローアップ → GPT standalone rewrite → ベクトル検索
    ├─ タグ抽出 → Elasticsearch パスフィルタ
    ├─ Qdrant チャンクベクトル検索 (limit × 3 → ファイル単位マージ → top-k)
    ├─ parent_text ベースのコンテキスト構成 (max 110K トークン)
    └─ GPT-4o-mini / GPT-5-mini 回答生成
    │
    ▼
[sync_documents.py] 10分周期
    ├─ MD5ハッシュベース変更検出
    ├─ ヘッダーベースチャンキング (512トークン、50 overlap)
    ├─ Qdrant チャンク upsert
    └─ Elasticsearch ファイル単位 bulk index
```

---

## 技術スタック

| 役割 | 技術 |
|------|------|
| Web Framework | FastAPI (Python 3.11+) |
| Vector DB | Qdrant Cloud |
| Full-text Search | Elasticsearch 8.18 |
| Cache | Redis 7.2 (TTL 30分) |
| LLM | GPT-4o-mini / GPT-5-mini |
| Embedding | text-embedding-3-small (1536dim) |
| Container | Docker + Docker Compose |

---

## クイックスタート

### 1. リポジトリのクローン

```bash
git clone https://github.com/wonhongChang/ObsidianRagChat.git
cd ObsidianRagChat
```

### 2. 環境変数の設定

`.env` ファイルを作成：

```bash
# 必須
OPENAI_API_KEY=sk-...
QDRANT_URL=https://your-cluster.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault

# Docker内部サービス (変更不要)
ELASTICSEARCH_HOST=http://elasticsearch:9200
REDIS_HOST=redis
REDIS_PORT=6379

# オプション
CACHE_TTL=1800        # Redis TTL (秒、デフォルト30分)
INTERVAL_SECONDS=600  # 同期間隔 (秒、デフォルト10分)
```

### 3. 実行

```bash
docker-compose up -d

# ログ確認
docker-compose logs -f web
docker-compose logs -f sync
```

### 4. アクセス

```
http://localhost:8001
```

---

## 使用方法

#### 一般的な質問
```
"Obsidian RAG Chatの同期方法を教えて"
→ 全ノートのベクトル検索 (デフォルト top_k=5)
```

#### タグフィルター
```
"#interview タグの文書から面接準備方法を教えて"
→ interview タグの文書のみ検索
```

#### フォローアップ
```
質問1: "Redisのキャッシュ戦略を説明して"
質問2: "じゃあTTLはどう設定する？"
→ 会話履歴をもとに standalone rewrite してから検索
```

---

## API

| Method | Endpoint | 説明 |
|--------|----------|------|
| `POST` | `/api/search` | RAG検索 (メイン) |
| `DELETE` | `/api/cache` | キャッシュ全削除 |
| `GET` | `/api/cache/stats` | キャッシュ統計 |
| `GET` | `/api/notes/count` | 全ノート数 |
| `GET` | `/health` | ヘルスチェック |

**POST /api/search リクエストパラメータ：**

```json
{
  "query": "質問内容",
  "top_k": 5,
  "model": "gpt-4o-mini",
  "ignore_token_limit": false,
  "history": []
}
```

---

## プロジェクト構造

```
ObsidianRagChat/
├── app.py                     # FastAPIサーバー、キャッシュ/質問判定ルーティング
├── sync_documents.py          # 増分同期 (ハッシュベース)
│
├── embed/
│   ├── chunker.py             # ヘッダーベースチャンキング + スライディングウィンドウ
│   ├── embedder.py            # OpenAI埋め込み (バッチインデックス安全処理)
│   ├── document_loader.py     # マークダウンローダー
│   └── vector_store.py        # Qdrantクライアント
│
├── rag/
│   └── generator.py           # 検索 + コンテキスト構成 + GPT呼び出し
│
├── search/
│   ├── document_index.py      # Elasticsearch (lowercase_normalizer)
│   ├── cache.py               # Redisキャッシング + クエリ正規化
│   └── question_detector.py   # 独立/フォローアップ判定 (ルールベース)
│
├── scripts/
│   ├── clear_cache.py
│   └── clear_qdrant.py
│
├── tests/
│   └── test_question_detector.py
│
├── templates/
│   └── chat.html
│
├── docker-compose.yml
├── Dockerfile.web
├── Dockerfile.sync
└── requirements.txt
```

---

## 主要コマンド

```bash
# キャッシュ初期化
docker-compose exec web python scripts/clear_cache.py
curl -X DELETE http://localhost:8001/api/cache

# Qdrant初期化 (再同期が必要な場合)
docker-compose exec web python scripts/clear_qdrant.py
docker-compose restart sync

# ESインデックス再作成 (lowercase_normalizer適用)
curl -X DELETE http://localhost:9201/obsidian_notes
docker-compose restart sync

# テスト
docker-compose exec web python -m pytest tests/ -v
```

---

## トラブルシューティング

**検索結果なし**
```bash
curl http://localhost:9201/_cluster/health
curl http://localhost:8001/api/notes/count
```

**タグフィルターが効かない** — ESインデックスの再作成が必要 (上記コマンド参照)

**応答が遅い** — `rag_query.log` でボトルネック確認、top_k を減らす

**Dockerビルド失敗**
```bash
docker-compose build --no-cache
docker-compose down -v && docker-compose up -d
```

---

## セキュリティ

- `.env` ファイルは絶対にコミットしないでください (`.gitignore` に含まれています)
- `OPENAI_API_KEY`、`QDRANT_API_KEY` の外部公開禁止
