# 🧠 Obsidian RAG Chat

> **個人ノートをAIアシスタントに変える知能型検索システム**

Obsidianノートを RAG(Retrieval-Augmented Generation) システムに変換し、GPTと自然に対話できるWebインターフェースです。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)](https://fastapi.tiangolo.com/)

---

## ✨ 主な特徴

### 🎯 コア機能
- **🔍 ハイブリッド検索**: Elasticsearch + Qdrant ベクトルDBで精度と速度を向上
- **⚡ スマートキャッシング**: Redisベースの応答キャッシュで~20倍の高速化（コスト100%削減）
- **🤖 知能的な質問検出**: ルールベース + GPT-4o-miniで独立/フォローアップ質問を自動分類（90% GPT呼び出し削減）
- **🏷️ タグフィルタリング**: `#Subway`、`#RagChat`などのタグベース文書検索
- **💬 会話コンテキスト維持**: 過去の会話履歴を活用した自然な対話
- **🔄 リアルタイム同期**: 10分ごとにObsidian vaultの変更を自動検出（増分更新）

### 💡 最適化（2025-11-11適用）
- **📊 トークンカウントキャッシング**: LRUキャッシュで重複エンコーディング削除（-70~85%時間）
- **🎯 ルールベース質問検出**: 90% GPT API呼び出し削減（-0.5~2秒）
- **🚀 動的ESサイズ調整**: 必要な分だけリクエスト（-60%検索時間）
- **⚡ デフォルトtop_k=5**: 不要なノート削除（-27.6%応答時間、-69%トークン）
- **💰 コストの透明性**: リアルタイムでトークン使用量と推定コストを表示
- **📈 スケーラビリティ**: 10万以上のノートまで拡張可能なアーキテクチャ

---

## 🧠 RAGとは？

**RAG (Retrieval-Augmented Generation)** = 検索ベースの生成

```
┌─────────────┐
│ユーザー質問 │  "#Subwayタグ文書から中目黒から東新宿への行き方を教えて"
└──────┬──────┘
       ↓
┌──────────────────────────────────┐
│  1️⃣ ルールベース質問検出          │  → #タグ開始 = 独立質問 (0秒)
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  2️⃣ Redisキャッシュチェック       │  → ヒット時に即座に返却 ⚡ (0.001秒)
└──────┬───────────────────────────┘
       ↓ (ミス)
┌──────────────────────────────────┐
│  3️⃣ タグ抽出 (#Subway)            │
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  4️⃣ Elasticsearchフィルタリング   │  → 1個の文書 (タグ一致, 0.006秒)
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  5️⃣ クエリ埋め込み生成             │  → OpenAI API (0.58秒)
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  6️⃣ Qdrantベクトル検索 (5個)      │  → 類似度順にソート (1.08秒)
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  7️⃣ トークンカウント (LRUキャッシュ) │  → 即座に完了 (~0秒)
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  8️⃣ GPT-4o-mini回答生成           │  → "中目黒から..." (1.9秒)
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  9️⃣ Redisキャッシング & 応答      │  → TTL: 30分
└──────────────────────────────────┘

総処理時間: 3.58秒 (改善前: 6~16秒)
```

---

## 🛠️ 技術スタック

### バックエンド
- **フレームワーク**: FastAPI (Python 3.11+)
- **ベクトルDB**: Qdrant Cloud (1GB無料ティア)
- **検索エンジン**: Elasticsearch 8.18
- **キャッシュ**: Redis 7.2 (TTL: 30分)

### AI/ML
- **LLM**: OpenAI GPT-4o-mini / GPT-5-mini
- **埋め込み**: text-embedding-3-small (1536次元)
- **トークンカウント**: tiktoken (cl100k_base) + LRUキャッシュ

### インフラストラクチャ
- **コンテナ**: Docker + Docker Compose
- **同期**: 増分同期（10分間隔、Hash-ベース変更検出）
- **ストレージ**: Obsidian vault（マウント）

### フロントエンド
- **UI**: Vanilla JavaScript（レスポンシブ）
- **テンプレート**: Jinja2
- **スタイリング**: CSS3（グラデーションデザイン）

---

## 📦 クイックスタート（Docker推奨）

### 1️⃣ リポジトリのクローン

```bash
git clone https://github.com/yourusername/ObsidianRagChat.git
cd ObsidianRagChat
```

### 2️⃣ 環境変数の設定

`.env` ファイルを作成：

```bash
# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key

# Qdrant Cloud
QDRANT_URL=https://your-cluster.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key

# Elasticsearch (Docker内部)
ELASTICSEARCH_HOST=elasticsearch
ELASTICSEARCH_PORT=9200

# Redis (Docker内部)
REDIS_HOST=redis
REDIS_PORT=6379

# Obsidian Vault
OBSIDIAN_VAULT_PATH=/mnt/vault  # Docker内部パス
```

### 3️⃣ Obsidian Vaultパスの設定

`docker-compose.yml`のvolumesパスを修正：

```yaml
volumes:
  - /path/to/your/obsidian/vault:/mnt/vault:ro  # 実際のパスに変更
```

### 4️⃣ Dockerの実行

```bash
# コンテナのビルドと実行
docker-compose up -d

# ログ確認
docker-compose logs -f web
docker-compose logs -f sync
```

### 5️⃣ Webインターフェースへのアクセス

```
http://localhost:8001
```

---

## 🚀 使用方法

### 💬 基本的な使用

#### 一般的な質問
```
質問: "Obsidian RAG Chatについて教えて"
→ 全ノートから関連コンテンツを検索（デフォルト5個）
→ 処理時間: ~13.7秒、トークン: 25,739個
```

#### タグベース検索（最高パフォーマンス ⚡）
```
質問: "#Subwayタグ文書から中目黒から東新宿への行き方を教えて"
→ Subwayタグの文書のみ検索（1個）
→ 処理時間: ~3.6秒、トークン: 273個
```

#### フォローアップ質問
```
質問1: "#interview文書の面接準備事項を教えて"
質問2: "自己紹介はどう準備する?"
→ 履歴からタグを継承 (#interview)
→ 会話コンテキストを維持
```

### ⚙️ UIコントロール

#### 最大ノート数
- **5個（推奨 ⚡）**: 高速で十分な回答品質（デフォルト）
- **6-20個（普通）**: より多くのコンテキストが必要な場合
- **21-50個（遅い ⏳）**: 包括的検索
- **51個以上（非常に遅い 🐌）**: 全体検索（警告表示）

#### AIモデル選択
- **GPT-4o-mini**: 高速で低コスト（$0.15/1M入力）
- **GPT-5-mini**: ハイパフォーマンス（$0.25/1M入力）

#### 最大コンテキストトークン
- **デフォルト**: 110,000トークン
- **最大**: 180,000トークン（有効時）

#### 会話の初期化
履歴の蓄積を防ぎ、キャッシングを最適化

---

## 📊 パフォーマンス指標

### 🎯 検索パフォーマンス（2025-11-11測定）

**タグフィルター検索**（最適）:
| 項目 | キャッシュミス | キャッシュヒット | 改善率 |
|------|-----------|-----------|-------|
| 応答時間 | 3.58秒 | 0.001秒 | **3,580倍** ⚡ |
| トークン使用 | 273 | 0 | **100%** 削減 💰 |
| APIコスト | ~$0.0001 | $0.000 | **無料** ✅ |

**一般検索**（top_k=5）:
| 項目 | キャッシュミス | キャッシュヒット | 改善率 |
|------|-----------|-----------|-------|
| 応答時間 | 13.69秒 | 0.001秒 | **13,690倍** ⚡ |
| トークン使用 | 25,739 | 0 | **100%** 削減 💰 |
| APIコスト | ~$0.004 | $0.000 | **無料** ✅ |

**比較**（top_k影響）:
| 設定 | 処理時間 | トークン使用量 | 改善効果 |
|------|----------|----------|----------|
| top_k=5（推奨） | 13.69秒 | 25,739 | **基準** |
| top_k=359（全体） | 18.91秒 | 82,964 | -27.6%遅い |

### 📈 キャッシュ統計

| 質問タイプ | キャッシュヒット率 | 平均削減額 |
|---------|-----------|---------|
| 独立質問 | 60-80% | $0.003/クエリ |
| フォローアップ | 20-40% | $0.001/クエリ |
| **平均** | **~72%** | **$0.002/クエリ** |

### 💰 コスト分析

**月1000クエリ基準**（top_k=5）:
- **キャッシング前**: $4.00
- **キャッシング後（72%ヒット）**: $1.12
- **削減額**: $2.88（72%削減）

**top_k比較**（キャッシング前）:
- **top_k=5**: $4.00/月
- **top_k=359**: $13.00/月
- **削減額**: $9.00（69%削減）

---

## 📁 プロジェクト構造

```
ObsidianRagChat/
├── 📄 app.py                          # FastAPI Webサーバー
├── 📄 sync_documents.py               # 増分同期（10分、Hash-ベース）
│
├── 📂 embed/                          # 埋め込み & ベクトルDB
│   ├── embedder.py                    # OpenAI埋め込み
│   ├── document_loader.py             # マークダウンローダー
│   └── vector_store.py                # Qdrantクライアント（増分更新）
│
├── 📂 rag/                            # RAGエンジン
│   └── generator.py                   # 検索 + GPT生成（最適化済み）
│
├── 📂 search/                         # 検索 & キャッシング
│   ├── document_index.py              # Elasticsearchクライアント
│   ├── cache.py                       # Redisキャッシング（独立質問検出）
│   └── question_detector.py           # 質問検出（ルール + GPT）
│
├── 📂 scripts/                        # ユーティリティ
│   ├── clear_cache.py                 # キャッシュ削除
│   ├── clear_qdrant.py                # Qdrant初期化
│   ├── migrate_qdrant_payload.py      # DBマイグレーション
│   └── add_qdrant_index.py            # タグインデックス作成
│
├── 📂 tests/                          # テスト
│   └── test_question_detector.py      # 質問検出テスト（22個）
│
├── 📂 templates/                      # フロントエンド
│   └── chat.html                      # チャットUI（パフォーマンス警告含む）
│
├── 📄 docker-compose.yml              # Docker構成
├── 📄 Dockerfile.web                  # Webサーバーイメージ
├── 📄 Dockerfile.sync                 # 同期イメージ
├── 📄 requirements.txt                # Pythonパッケージ
├── 📄 .env                            # 環境変数（非公開）
│
└── 📄 README.md                       # 韓国語README
```

---

## 🐳 Dockerサービス

```yaml
services:
  web (FastAPI)      # ポート 8001:8000
  sync (バッチ)      # 10分ごとに実行
  elasticsearch      # ポート 9201:9200
  redis              # ポート 6379:6379
```

### 主要コマンド

```bash
# 全体再起動
docker-compose restart

# ログ確認
docker-compose logs -f web
docker-compose logs -f sync

# キャッシュ初期化
docker-compose exec web python scripts/clear_cache.py
curl -X DELETE http://localhost:8001/api/cache

# Qdrant初期化
docker-compose exec web python scripts/clear_qdrant.py

# キャッシュ統計
curl http://localhost:8001/api/cache/stats

# 全ノート数
curl http://localhost:8001/api/notes/count

# コンテナ状態
docker-compose ps

# 停止
docker-compose down
```

---

## 💡 最適化のヒント

### 🎯 コスト削減

1. **キャッシング活用**: 同じ質問の繰り返しで無料
2. **top_k=5使用**: デフォルト値維持で69%コスト削減
3. **タグフィルタリング**: 検索範囲縮小でトークン90%削減
4. **GPT-4o-mini使用**: GPT-4と比較して15倍安い
5. **会話初期化**: 履歴蓄積を防止

### ⚡ 速度向上

1. **タグ活用**: 3.6秒（vs 一般13.7秒）
2. **独立質問優先**: フォローアップよりキャッシュヒット率2倍
3. **Redisキャッシング**: 3,500倍以上の高速化
4. **ルールベース検出**: GPT呼び出し90%削減（-0.5~2秒）
5. **LRUキャッシング**: トークンカウント重複削除（-70~85%）

### 🎓 精度向上

1. **具体的な質問**: "それ"の代わりに明示的なトピックを言及
2. **タグベース検索**: 関連文書のみ検索
3. **最大トークンモード**: より多くのコンテキストを活用
4. **会話コンテキスト維持**: フォローアップ質問を活用
5. **適切なtop_k**: 5-20個推奨（50個以上は非効率的）

---

## 📈 今後の計画

### 短期（1-2週間）
- [ ] ストリーミング応答（リアルタイム回答出力）
- [ ] キャッシュ有効性検証（文書変更時自動無効化）
- [ ] 使用統計ダッシュボード

### 中期（1-3ヶ月）
- [ ] MCP（Model Context Protocol）統合（[戦略文書](./MCP_INTEGRATION_STRATEGY.md)）
- [ ] ハイブリッド検索（BM25 + Vector）
- [ ] マルチユーザーサポート（テナントID）
- [ ] Rerankerモデル（Cohere）

### 長期（3-6ヶ月）
- [ ] ローカルLLMサポート（Llama 3.1）
- [ ] 埋め込みキャッシング（コスト追加削減）
- [ ] Prometheus + Grafanaモニタリング
- [ ] マイクロサービスアーキテクチャ

---

## 📚 関連ドキュメント

- **[インデックス & キャッシングアーキテクチャ](./INDEXING_AND_CACHING_ARCHITECTURE.md)** - 面接対策技術文書 ⭐
- **[パフォーマンス分析レポート](./RAG_PERFORMANCE_ANALYSIS.md)** - ボトルネック分析と改善案
- **[MCP統合戦略](./MCP_INTEGRATION_STRATEGY.md)** - Model Context Protocol導入計画
- **[ファイル名リファクタリング](./FILENAME_REVIEW.md)** - ネーミング哲学と変更履歴

---

## 🤝 貢献

イシューとPRを歓迎します！

### 開発環境のセットアップ

```bash
# リポジトリのフォークとクローン
git clone https://github.com/your-username/ObsidianRagChat.git

# ブランチ作成
git checkout -b feature/amazing-feature

# 変更をコミット
git commit -m "Add amazing feature"

# PRの作成
git push origin feature/amazing-feature
```

### コーディングガイド

- Python 3.11+使用
- Type hintsは必須
- Docstring作成を推奨
- テストを追加（`tests/`フォルダ）
- ファイル名は内容を明確に表現（例: `generator.py` > `gpt_rag.py`）

---

## 🧪 テスト

```bash
# 全テスト実行
docker-compose exec web python -m pytest tests/ -v

# 特定テスト
docker-compose exec web python -m pytest tests/test_question_detector.py -v

# テスト結果（22個のテスト）
============================= test session starts ==============================
collected 22 items

tests/test_question_detector.py::test_rephrase_exact_match PASSED        [  4%]
tests/test_question_detector.py::test_rule_hashtag_start PASSED          [ 18%]
tests/test_question_detector.py::test_rule_pronoun_start_korean PASSED   [ 27%]
...
============================== 22 passed in 3.31s ===============================
```

---

## 📝 ライセンス

MIT License - 自由に使用、修正、配布可能

---

## 🙏 謝辞

このプロジェクトは以下のオープンソースプロジェクトのおかげで実現しました：

- **[OpenAI](https://openai.com/)** - GPTモデルと埋め込みAPI
- **[Qdrant](https://qdrant.tech/)** - 高性能ベクトルデータベース
- **[Elasticsearch](https://www.elastic.co/)** - 強力な全文検索エンジン
- **[Redis](https://redis.io/)** - 高速インメモリキャッシング
- **[FastAPI](https://fastapi.tiangolo.com/)** - モダンなWebフレームワーク
- **[Docker](https://www.docker.com/)** - コンテナプラットフォーム
- **[Obsidian](https://obsidian.md/)** - 最高の知識管理ツール

---

## 📞 お問い合わせとサポート

- **Issues**: [GitHub Issues](https://github.com/yourusername/ObsidianRagChat/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/ObsidianRagChat/discussions)

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/yourusername">Your Name</a>
</p>

<p align="center">
  <sub>⭐ このプロジェクトが役に立った場合は、Starをお願いします！</sub>
</p>
