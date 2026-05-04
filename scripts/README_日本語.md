# ユーティリティスクリプト

管理・メンテナンス用スクリプト一覧です。

---

## clear_cache.py

**用途**: Redis キャッシュ全削除

```bash
docker-compose exec web python scripts/clear_cache.py
```

**使用タイミング**
- コード変更後に古いキャッシュを削除したいとき
- テスト後のクリーンアップ

---

## clear_qdrant.py

**用途**: Qdrant コレクション全初期化 (ベクターデータ削除)

```bash
docker-compose exec web python scripts/clear_qdrant.py
```

> ⚠️ 全ベクターデータが削除されます。次回 sync 実行時に自動再生成されます。

**使用タイミング**
- ノートの埋め込みを最初からやり直したいとき
- Qdrant コレクション構造を変更した後

---

## add_qdrant_index.py

**用途**: Qdrant `path` フィールドに keyword インデックスを追加 (検索性能向上)

```bash
docker-compose exec web python scripts/add_qdrant_index.py
```

> ℹ️ 一回限りの最適化スクリプト。実行済みの場合は再実行不要。

**使用タイミング**
- 初回インストール後にタグフィルター検索の性能を上げたいとき
- `MatchAny` フィルターエラーが発生したとき


---

## 注意事項

- すべてのスクリプトは **Docker コンテナ内部** (`docker-compose exec web`) で実行してください
- `clear_qdrant.py` 実行後は必ず `docker-compose restart sync` で再同期してください
