import os
import sys
import time
from embed.document_loader import load_markdown_files
from embed.embedder import embed_texts
from embed.chunker import chunk_document
from rag.model_config import retrieval_mode
from qdrant_client.models import PointStruct, PointIdsList
from search.document_index import index_documents_bulk, delete_document, get_indexed_documents

# ============================================
# 설정
# ============================================
INTERVAL_SECONDS = int(os.getenv("INTERVAL_SECONDS", "600"))   # 10분 (600초)

def clear_cache_safely():
    """문서 변경 후 Redis 캐시를 비우되, 실패해도 동기화 결과는 보존한다."""
    try:
        from search.cache import clear_all_cache
        clear_all_cache()
    except Exception as e:
        print(f"⚠️  캐시 초기화 실패 (동기화는 유지): {e}")

# ============================================
# 변경 감지 및 동기화
# ============================================
def sync_all():
    """Reconcile active indexes; never open or mutate Qdrant in lexical mode."""
    all_docs = load_markdown_files()
    hybrid = retrieval_mode() == "hybrid"
    if hybrid:
        from embed.vector_store import get_existing_documents, client, COLLECTION_NAME, ensure_collection_exists
        existing_docs = get_existing_documents()
    else:
        existing_docs = {}
    indexed_docs = get_indexed_documents()
    current_paths = {doc["path"] for doc in all_docs}
    to_embed = [
        doc for doc in all_docs
        if existing_docs.get(doc["path"], {}).get("hash") != doc["hash"]
    ] if hybrid else []
    to_index = [
        doc for doc in all_docs if indexed_docs.get(doc["path"]) != doc["hash"]
    ]
    deleted_paths = (set(existing_docs) | set(indexed_docs)) - current_paths
    stats = {
        "vector_documents": len(to_embed),
        "es_documents": len(to_index),
        "deleted_documents": len(deleted_paths),
    }
    if not to_embed and not to_index and not deleted_paths:
        return stats

    mutated = False
    try:
        for doc in to_embed:
            chunks = chunk_document(doc)
            if not chunks:
                raise ValueError("A non-empty indexed document must produce chunks")
            vectors = embed_texts([
                f"파일명: {chunk['filename']}\n{chunk['chunk_text']}" for chunk in chunks
            ])
            if len(vectors) != len(chunks) or any(not vector for vector in vectors):
                raise ValueError("Incomplete embedding batch; existing vectors preserved")
            if len({len(vector) for vector in vectors}) != 1:
                raise ValueError("Inconsistent embedding dimensions")
            ensure_collection_exists(len(vectors[0]))
            points = [
                PointStruct(
                    id=chunk["point_id"], vector=vector,
                    payload={key: value for key, value in chunk.items() if key != "point_id"},
                )
                for chunk, vector in zip(chunks, vectors)
            ]
            # Hash-based IDs let old and new generations coexist during upload.
            mutated = True
            for i in range(0, len(points), 100):
                client.upsert(
                    collection_name=COLLECTION_NAME, points=points[i:i + 100], wait=True,
                )
            new_ids = {point.id for point in points}
            stale_ids = [
                point_id for point_id in existing_docs.get(doc["path"], {}).get("chunk_ids", [])
                if point_id not in new_ids
            ]
            if stale_ids:
                client.delete(
                    collection_name=COLLECTION_NAME,
                    points_selector=PointIdsList(points=stale_ids), wait=True,
                )

        if to_index:
            mutated = True
            index_documents_bulk(to_index)

        for path in sorted(deleted_paths):
            mutated = True
            ids = existing_docs.get(path, {}).get("chunk_ids", [])
            if ids:
                client.delete(
                    collection_name=COLLECTION_NAME,
                    points_selector=PointIdsList(points=ids), wait=True,
                )
            if path in indexed_docs:
                delete_document(path)
    finally:
        # A failed request may still have partially changed an index.
        if mutated:
            clear_cache_safely()

    print(f"Sync completed: {stats}")
    return stats


# ============================================
# Elasticsearch 연결 대기
# ============================================
def wait_for_elasticsearch(max_retries=30, delay=2):
    """Elasticsearch가 준비될 때까지 대기"""
    from elasticsearch import Elasticsearch

    es_host = os.getenv("ELASTICSEARCH_HOST", "http://elasticsearch:9200")
    es = Elasticsearch([es_host])

    print(f"⏳ Elasticsearch 연결 대기 중... ({es_host})")

    for i in range(max_retries):
        try:
            if es.ping():
                print(f"✅ Elasticsearch 연결 성공!")
                return True
        except Exception as e:
            print(f"   시도 {i+1}/{max_retries}: 대기 중... ({delay}초)")
        time.sleep(delay)

    print(f"❌ Elasticsearch 연결 실패 (최대 재시도 횟수 초과)")
    return False


# ============================================
# 메인
# ============================================
def main():
    """메인 실행 함수"""

    # Elasticsearch 연결 대기
    if not wait_for_elasticsearch():
        print("❌ Elasticsearch에 연결할 수 없습니다. 종료합니다.")
        sys.exit(1)

    once_mode = "--once" in sys.argv

    print("🚀 Obsidian Notes 동기화")
    print(f"   • 실행 간격: {INTERVAL_SECONDS//60}분")
    print(f"   • 모드: {'한 번만 실행' if once_mode else '백그라운드 실행'}")

    if once_mode:
        # 한 번만 실행
        sync_all()
    else:
        # 백그라운드 실행
        print("\n⏰ 백그라운드 동기화 시작 (Ctrl+C로 중지)")

        while True:
            try:
                sync_all()
                print(f"\n⏰ 다음 실행까지 {INTERVAL_SECONDS//60}분 대기 중...")
                time.sleep(INTERVAL_SECONDS)
            except KeyboardInterrupt:
                print("\n\n👋 동기화를 중지합니다.")
                break
            except Exception as e:
                print(f"\n❌ 오류 발생: {e}")
                import traceback
                traceback.print_exc()
                print(f"\n⏰ {INTERVAL_SECONDS//60}분 후 재시도합니다...")
                time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
