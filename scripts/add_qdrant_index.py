#!/usr/bin/env python3
"""
Qdrant path 필드에 인덱스 추가

MatchAny 필터를 사용하기 위해 path 필드를 인덱싱합니다.
"""

from embed.vector_store import client, COLLECTION_NAME
from qdrant_client.models import PayloadSchemaType

def add_path_index():
    """path 필드에 keyword 인덱스 추가"""

    print("🔍 Qdrant collection 정보 조회 중...")

    try:
        # Collection 정보 확인
        collection_info = client.get_collection(collection_name=COLLECTION_NAME)
        print(f"✅ Collection: {COLLECTION_NAME}")
        print(f"   Points: {collection_info.points_count}")

        # path 필드에 keyword 인덱스 추가
        print(f"\n⚙️  path 필드에 인덱스 추가 중...")
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="path",
            field_schema=PayloadSchemaType.KEYWORD
        )

        print(f"✅ path 필드 인덱스 추가 완료!")

        # 인덱스 확인
        print(f"\n🔍 인덱스 확인 중...")
        updated_info = client.get_collection(collection_name=COLLECTION_NAME)

        if updated_info.payload_schema:
            print(f"✅ 현재 payload 인덱스:")
            for field_name, field_info in updated_info.payload_schema.items():
                print(f"   - {field_name}: {field_info}")
        else:
            print(f"   (payload_schema 정보 없음, 하지만 인덱스는 추가됨)")

        print(f"\n✅ 완료! 이제 path 필드로 MatchAny 필터를 사용할 수 있습니다.")

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Qdrant path 필드 인덱스 추가")
    print("=" * 70)
    print()
    print("⚠️  주의: 이 작업은 collection에 인덱스를 추가합니다.")
    print("         데이터는 변경되지 않으며, 쿼리 성능이 향상됩니다.")
    print()

    response = input("계속하시겠습니까? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        print()
        add_path_index()
        print()
        print("=" * 70)
        print("✅ 인덱스 추가 완료!")
        print("=" * 70)
    else:
        print("취소되었습니다.")
