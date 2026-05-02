import os
import sys
import time
from datetime import datetime
from embed.document_loader import load_markdown_files
from embed.embedder import embed_texts
from embed.vector_store import get_existing_documents, client, COLLECTION_NAME, get_path_id, ensure_collection_exists
from qdrant_client.models import PointStruct
from search.document_index import index_documents_bulk, delete_document

# ============================================
# 설정
# ============================================
INTERVAL_SECONDS = int(os.getenv("INTERVAL_SECONDS", "600"))   # 10분 (600초)

# ============================================
# 변경 감지 및 동기화
# ============================================
def sync_all():
    """10분마다 전체 파일 체크 및 변경사항 처리"""
    print(f"\n{'='*70}")
    print(f"🔄 동기화 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    # 1. 모든 마크다운 파일 로드
    print("🔍 파일 로드 중...")
    all_docs = load_markdown_files()

    # 2. Qdrant의 기존 문서 가져오기
    existing_docs = get_existing_documents()

    # 3. 변경 감지
    new_files = []
    updated_files = []
    unchanged_files = []

    for doc in all_docs:
        path = doc["path"]
        if path not in existing_docs:
            # 새 파일
            new_files.append(doc)
        elif doc["hash"] != existing_docs[path]["hash"]:
            # 수정된 파일
            updated_files.append(doc)
        else:
            # 변경 없음
            unchanged_files.append(doc)

    # 4. 삭제된 파일 감지
    current_paths = {doc["path"] for doc in all_docs}
    existing_paths = set(existing_docs.keys())
    deleted_paths = existing_paths - current_paths

    # 5. 통계 출력
    print(f"\n📊 변경 감지 결과:")
    print(f"   • 새 파일: {len(new_files)}개")
    print(f"   • 수정된 파일: {len(updated_files)}개")
    print(f"   • 삭제된 파일: {len(deleted_paths)}개")
    print(f"   • 변경 없음: {len(unchanged_files)}개")

    # 6. 변경사항이 없으면 종료
    if not new_files and not updated_files and not deleted_paths:
        print("\n✅ 변경사항이 없습니다.")
        print(f"{'='*70}")
        return

    # 7. 삭제된 파일 처리
    if deleted_paths:
        print(f"\n🗑️  {len(deleted_paths)}개 파일 삭제 중...")
        # Qdrant 삭제
        delete_ids = [existing_docs[path]["id"] for path in deleted_paths]
        client.delete(collection_name=COLLECTION_NAME, points_selector=delete_ids)

        # Elasticsearch 삭제
        for path in deleted_paths:
            delete_document(path)

        print(f"   ✅ 삭제 완료")

    # 8. 새 파일 + 수정된 파일 처리
    to_process = new_files + updated_files

    if to_process:
        print(f"\n⚡ {len(to_process)}개 파일 처리 중...")

        # 파일 목록 출력
        for doc in to_process:
            file_type = "🆕 NEW" if doc in new_files else "🔄 UPDATE"
            print(f"   {file_type}: {doc['filename']}")

        # 임베딩 생성
        print(f"\n   🧠 임베딩 생성 중...")
        texts = [doc["text"] for doc in to_process]
        vectors = embed_texts(texts)

        # Qdrant 업로드
        print(f"   ⬆️  Qdrant 업로드 중...")
        ensure_collection_exists(len(vectors[0]))

        points = []
        for i, doc in enumerate(to_process):
            point_id = get_path_id(doc["path"])
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vectors[i],
                    payload={
                        "path": doc["path"],        # ID 역할 (ES 조회용)
                        "filename": doc["filename"]  # 결과 표시용
                    }
                )
            )

        client.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"   ✅ Qdrant 업로드 완료")

        # Elasticsearch 인덱싱
        print(f"   📇 Elasticsearch 인덱싱 중...")
        index_documents_bulk(to_process)

        print(f"\n✅ {len(to_process)}개 파일 처리 완료")

    print(f"{'='*70}")


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
