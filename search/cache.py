import redis
import json
import os
from dotenv import load_dotenv
import hashlib

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "1800"))  # 30분

# Redis 클라이언트 생성
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True
)

def get_cache_key(prefix, query):
    """쿼리를 해시하여 캐시 키 생성"""
    query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
    return f"{prefix}:{query_hash}"

def get_cached_rag(query):
    """RAG 응답 캐시 조회"""
    key = get_cache_key("rag", query)
    cached = redis_client.get(key)

    if cached:
        print(f"🎯 RAG 캐시 히트: {query[:50]}...")
        return json.loads(cached)

    return None

def set_cached_rag(query, result, ttl=CACHE_TTL):
    """RAG 응답 캐시 저장"""
    key = get_cache_key("rag", query)
    redis_client.setex(key, ttl, json.dumps(result, ensure_ascii=False))
    print(f"💾 RAG 캐시 저장: {query[:50]}...")

def clear_all_cache():
    """모든 캐시 삭제"""
    redis_client.flushdb()
    print("✅ 모든 캐시 삭제 완료")

def get_cache_stats():
    """캐시 통계"""
    info = redis_client.info("stats")
    return {
        "total_keys": redis_client.dbsize(),
        "hits": info.get("keyspace_hits", 0),
        "misses": info.get("keyspace_misses", 0),
        "memory_used": redis_client.info("memory")["used_memory_human"]
    }