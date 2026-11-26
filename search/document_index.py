from elasticsearch import Elasticsearch, NotFoundError
from dataclasses import dataclass
import os
import re
from dotenv import load_dotenv

load_dotenv()

ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
INDEX_NAME = "obsidian_notes"

# Elasticsearch 클라이언트 생성
es = Elasticsearch([ES_HOST])


@dataclass(frozen=True)
class LexicalHit:
    id: str
    score: float
    payload: dict


def search_lexical_notes(query: str, limit: int, filter_tags=None):
    """Rank existing ES documents and retain the original matching passages."""
    tags = sorted({t for tag in filter_tags or [] for t in (tag, tag.lower()) if t})
    terms = query
    if tags:
        terms = re.sub(r"#\w+|\w+\s*태그", " ", terms).strip()
    if not tags and not terms.strip():
        return []
    conditions = {}
    if tags:
        conditions["filter"] = [{"terms": {"tags": tags}}]
    if terms.strip():
        conditions["must"] = [{"multi_match": {
            "query": terms, "fields": ["filename^3", "text"],
        }}]
    try:
        response = es.search(
            index=INDEX_NAME, query={"bool": conditions}, size=min(limit * 3, 1000),
            source_includes=["path", "filename", "tags", "hash", "text"],
            highlight={
                "pre_tags": [""], "post_tags": [""], "order": "score",
                "fields": {"text": {"fragment_size": 350, "number_of_fragments": 4,
                                    "max_analyzed_offset": 500000}},
            },
            sort=[{"_score": "desc"}, {"path": "asc"}],
        )
    except NotFoundError as exc:
        error = exc.body.get("error") if isinstance(exc.body, dict) else None
        if isinstance(error, dict) and error.get("type") == "index_not_found_exception":
            return []
        raise

    seen = set()
    results = []
    for hit in response["hits"]["hits"]:
        doc = hit["_source"]
        path = doc["path"]
        identity = doc.get("hash") or path
        if identity in seen:
            continue
        body = doc.get("text") or ""
        snippets = list(dict.fromkeys(s.strip() for s in hit.get("highlight", {}).get("text", [])
                                      if s.strip() and s.strip() in body))
        # Filename matches and tag-only lists need a bounded excerpt even without highlights.
        if not snippets:
            snippets = [body[:1600].strip()] if body.strip() else []
        if not snippets:
            continue
        score = float(hit.get("_score") or 0)
        evidence = [{"id": f"{path}:{i}", "text": s, "score": score}
                    for i, s in enumerate(snippets[:4])]
        results.append(LexicalHit(path, score, {
            "path": path, "filename": doc.get("filename") or path,
            "tags": doc.get("tags") or [], "hash": doc.get("hash"),
            "chunk_text": evidence[0]["text"], "retrieved_chunks": evidence,
            "retrieval_method": "lexical",
        }))
        seen.add(identity)
        if len(results) >= limit:
            break
    return results

def get_indexed_documents():
    """Read ES independently so partial sync failures are repaired next time."""
    if not es.indices.exists(index=INDEX_NAME):
        return {}
    from elasticsearch.helpers import scan
    return {
        hit["_source"]["path"]: hit["_source"].get("hash")
        for hit in scan(
            es, index=INDEX_NAME,
            query={"query": {"match_all": {}}, "_source": ["path", "hash"]},
        )
    }

def ensure_index_exists():
    """인덱스가 없으면 생성"""
    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(
            index=INDEX_NAME,
            body={
                "settings": {
                    "analysis": {
                        "normalizer": {
                            "lowercase_normalizer": {
                                "type": "custom",
                                "filter": ["lowercase"]
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "path": {"type": "keyword"},
                        "filename": {"type": "text"},
                        "text": {
                            "type": "text",
                            "analyzer": "standard"
                        },
                        "tags": {
                            "type": "keyword",
                            "normalizer": "lowercase_normalizer"
                        },
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

    from elasticsearch.helpers import bulk

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

    success, failed = bulk(es, actions, raise_on_error=False, refresh="wait_for")
    if failed:
        raise RuntimeError(f"Elasticsearch bulk write failed for {len(failed)} documents")
    return success

def delete_document(path):
    """문서 삭제"""
    try:
        es.delete(index=INDEX_NAME, id=path, refresh="wait_for")
        print(f"✅ Elasticsearch에서 '{path}' 삭제 완료")
    except NotFoundError:
        pass
