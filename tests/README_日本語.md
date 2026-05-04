# テスト

## 公開テスト

### `test_question_detector.py`

フォローアップ判定ロジック (`search/question_detector.py`) のユニットテスト。
外部サービスへの依存なしでローカルからそのまま実行できます。

**実行方法**

```bash
# ローカル
python -m pytest tests/test_question_detector.py -v

# Docker
docker-compose exec web python -m pytest tests/test_question_detector.py -v
```

**テスト項目 (24件)**

| 分類 | テスト内容 |
|------|-----------|
| Rephrase判定 | 完全一致 / 類似度90%以上 / 包含関係 / 低類似度 |
| 独立質問ルール | #タグ始まり / ファイル名言及 / 疑問詞始まり / X について パターン / 長い質問(15語以上) / 定義・概念キーワード |
| フォローアップルール | 韓国語・日本語・英語の代名詞 / 代名詞 + について |
| エッジケース | 空のヒストリー / 空白処理 / 大文字小文字無視 / 多言語混在 |
| 保存・取得 | クエリ保存と取得 / 最大10件制限 / 初期化 |
| シナリオ | 多言語切り替えキャッシュ / フォローアップフロー |

## ローカル専用テスト (gitignore)

個人の Obsidian ノートデータを使用するテストは `.gitignore` に含まれており、公開されません。

```
tests/test_example*.py   # キャッシュシナリオテスト
tests/test_example*.md   # テストシナリオ定義
tests/test_search*.py    # 検索品質テスト
```
