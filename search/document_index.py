from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv

load_dotenv()

ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
INDEX_NAME = "obsidian_notes"

# Elasticsearch 클라이언트 생성
es = Elasticsearch([ES_HOST])

def ensure_index_exists():
    """인덱스가 없으면 생성"""
    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(
            index=INDEX_NAME,
            body={
                "mappings": {
                    "properties": {
                        "path": {"type": "keyword"},
                        "filename": {"type": "text"},
                        "text": {
                            "type": "text",
                            "analyzer": "standard"
                        },
                        "tags": {"type": "keyword"},
                        "mtime": {"type": "date"},
                        "hash": {"type": "keyword"}
                    }
                }
            }
        )
        print(f"✅ Elasticsearch 인덱스 '{INDEX_NAME}' 생성 완료")

def index_document(doc):
    """문서 인덱싱"""
    ensure_index_exists()

    es.index(
        index=INDEX_NAME,
        id=doc["path"],  # path를 고유 ID로 사용
        document={
            "path": doc["path"],
            "filename": doc["filename"],
            "text": doc["text"],
            "tags": doc["tags"],
            "mtime": int(doc["mtime"] * 1000),  # 초 → 밀리초 변환
            "hash": doc["hash"]
        }
    )

def index_documents_bulk(documents):
    """여러 문서를 한번에 인덱싱"""
    ensure_index_exists()

    from elasticsearch.helpers import bulk, BulkIndexError

    actions = [
        {
            "_index": INDEX_NAME,
            "_id": doc["path"],
            "_source": {
                "path": doc["path"],
                "filename": doc["filename"],
                "text": doc["text"],
                "tags": doc["tags"],
                "mtime": int(doc["mtime"] * 1000),  # 초 → 밀리초 변환
                "hash": doc["hash"]
            }
        }
        for doc in documents
    ]

    try:
        success, failed = bulk(es, actions, raise_on_error=False)

        # failed는 실패한 항목의 리스트일 수 있음
        failed_count = len(failed) if isinstance(failed, list) else failed

        if failed_count > 0:
            print(f"⚠️  {failed_count}개 문서 인덱싱 실패 (성공: {success}개)")
        else:
            print(f"✅ {len(documents)}개 문서 Elasticsearch 인덱싱 완료")

    except BulkIndexError as e:
        print(f"❌ Elasticsearch 인덱싱 에러: {e}")
        # 에러 발생해도 계속 진행
        print(f"   → 다음 배치에서 재시도됩니다.")
    except Exception as e:
        print(f"❌ 예상치 못한 에러: {e}")

def delete_document(path):
    """문서 삭제"""
    try:
        es.delete(index=INDEX_NAME, id=path)
        print(f"✅ Elasticsearch에서 '{path}' 삭제 완료")
    except Exception as e:
        print(f"⚠️  Elasticsearch 삭제 실패: {e}")