import redis
import json
import os
import re
from dotenv import load_dotenv
import hashlib
import logging

logger = logging.getLogger(__name__)
CACHE_VERSION = "v3"

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "1800"))  # 30분

# Redis 클라이언트 생성
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=2,
)

def normalize_query(query: str) -> str:
    return re.sub(r'\s+', ' ', query.strip().lower())

def get_cache_key(prefix, query):
    query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
    return f"{prefix}:{CACHE_VERSION}:{query_hash}"

def get_cached_rag(query):
    """RAG 응답 캐시 조회"""
    key = get_cache_key("rag", query)
    try:
        cached = redis_client.get(key)
        if cached:
            result = json.loads(cached)
            return result if isinstance(result, dict) else None
    except (redis.RedisError, ValueError):
        logger.warning("Response cache unavailable or invalid; treating as a miss")
    return None

def set_cached_rag(query, result, ttl=CACHE_TTL):
    """RAG 응답 캐시 저장"""
    key = get_cache_key("rag", query)
    try:
        redis_client.setex(key, ttl, json.dumps(result, ensure_ascii=False))
        return True
    except redis.RedisError:
        logger.warning("Response cache write failed; preserving the generated answer")
        return False

def clear_all_cache():
    """모든 캐시 삭제"""
    batch = []
    for key in redis_client.scan_iter(match="rag:*", count=500):
        batch.append(key)
        if len(batch) == 500:
            redis_client.delete(*batch)
            batch = []
    if batch:
        redis_client.delete(*batch)
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
