from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, PayloadSchemaType, PointIdsList
from dotenv import load_dotenv
import os
import hashlib

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

COLLECTION_NAME = "obsidian_notes"

def get_path_id(path):
    return int(hashlib.md5(path.encode('utf-8')).hexdigest(), 16) % (2**63)

def ensure_collection_exists(vector_size):
    """컬렉션이 없으면 생성"""
    collections = client.get_collections().collections
    collection_exists = any(c.name == COLLECTION_NAME for c in collections)
    
    if not collection_exists:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        print(f"✅ '{COLLECTION_NAME}' 컬렉션 생성 완료")
        
        # tags 필드에 대한 인덱스 생성
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="tags",
            field_schema=PayloadSchemaType.KEYWORD
        )
        print("✅ 태그 필드 인덱스 생성 완료")

def get_existing_documents():
    """DB에 있는 모든 문서의 메타데이터 가져오기"""
    try:
        existing_docs = {}
        offset = None
        while True:
            result, next_offset = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=1000,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            for point in result:
                path = point.payload.get("path")
                if path:
                    existing_docs[path] = {
                        "id": point.id,
                        "hash": point.payload.get("hash", ""),
                        "mtime": point.payload.get("mtime", 0)
                    }
            if next_offset is None:
                break
            offset = next_offset
        return existing_docs
    except Exception as e:
        print(f"⚠️  기존 문서 조회 실패 (새 컬렉션일 수 있음): {e}")
        return {}

def upload_vectors_incremental(documents, vectors):
    """
    증분 업데이트: 변경된 파일만 업데이트
    Args:
        documents: list of dict with keys: text, filename, path, tags, mtime, hash
        vectors: list of embeddings
    """
    # 컬렉션 존재 확인 및 생성
    ensure_collection_exists(len(vectors[0]))
    
    # 기존 문서 정보 가져오기
    existing_docs = get_existing_documents()
    existing_paths = set(existing_docs.keys())
    current_paths = set(doc["path"] for doc in documents)
    
    # 변경 분석
    new_files = []
    updated_files = []
    deleted_paths = existing_paths - current_paths
    
    for i, doc in enumerate(documents):
        path = doc["path"]
        if path not in existing_docs:
            # 새 파일
            new_files.append((i, doc))
        else:
            # 해시 비교로 변경 감지
            if doc["hash"] != existing_docs[path]["hash"]:
                updated_files.append((i, doc))
    
    # 통계 출력
    print(f"\n📊 변경 사항 분석:")
    print(f"   • 새 파일: {len(new_files)}개")
    print(f"   • 수정된 파일: {len(updated_files)}개")
    print(f"   • 삭제된 파일: {len(deleted_paths)}개")
    print(f"   • 변경 없음: {len(current_paths) - len(new_files) - len(updated_files)}개")
    
    # 삭제된 파일 처리
    if deleted_paths:
        delete_ids = [existing_docs[path]["id"] for path in deleted_paths]
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=PointIdsList(ids=delete_ids)
        )
        print(f"🗑️  {len(deleted_paths)}개 파일 삭제 완료")
    
    # 새 파일 및 수정된 파일 업로드
    to_upload = new_files + updated_files
    if to_upload:
        points = []
        for i, doc in to_upload:
            point_id = get_path_id(doc["path"])
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vectors[i],
                    payload={
                        "text": doc["text"],
                        "filename": doc["filename"],
                        "path": doc["path"],
                        "tags": doc["tags"],
                        "mtime": doc["mtime"],
                        "hash": doc["hash"]
                    }
                )
            )
        
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"✅ {len(points)}개 파일 업로드/업데이트 완료")
    else:
        print("✅ 변경 사항 없음 - 업데이트 불필요")
    
    # 태그 통계 출력
    all_tags = []
    for doc in documents:
        all_tags.extend(doc["tags"])
    
    if all_tags:
        from collections import Counter
        tag_counts = Counter(all_tags)
        print(f"\n📊 전체 태그 통계:")
        print(f"   • 총 {len(tag_counts)}개 태그")
        print(f"   • 상위 10개: {dict(list(tag_counts.most_common(10)))}")
