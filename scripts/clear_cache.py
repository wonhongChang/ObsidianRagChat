#!/usr/bin/env python3
"""Redis 캐시 전체 삭제"""

from search.redis_cache import clear_all_cache

if __name__ == "__main__":
    print("🗑️  Redis 캐시 삭제 중...")
    clear_all_cache()
    print("✅ 모든 캐시가 삭제되었습니다!")
