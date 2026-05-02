#!/usr/bin/env python3
"""Qdrant 컬렉션 초기화 스크립트"""

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "obsidian_notes"

print(f"🔗 Qdrant 연결 중... ({QDRANT_URL})")
client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

try:
    # 컬렉션 삭제
    print(f"🗑️  '{COLLECTION_NAME}' 컬렉션 삭제 중...")
    client.delete_collection(collection_name=COLLECTION_NAME)
    print(f"✅ '{COLLECTION_NAME}' 컬렉션이 삭제되었습니다")
    print("💡 다음 sync 실행 시 자동으로 재생성됩니다")
except Exception as e:
    print(f"⚠️  오류 발생: {e}")
    print("   (컬렉션이 이미 없을 수도 있습니다)")
