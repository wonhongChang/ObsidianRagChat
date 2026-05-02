#!/usr/bin/env python3
"""
Qdrant Payload 마이그레이션 스크립트

기존 Qdrant 데이터의 payload를 최소화합니다:
- 기존: text, filename, path, tags, mtime, hash
- 변경 후: path, filename만 유지
"""

from embed.vector_store import client, COLLECTION_NAME
from qdrant_client.models import PointStruct

def migrate_qdrant_payload():
    """Qdrant payload를 최소화하여 재업로드"""

    print("🔍 기존 Qdrant 데이터 조회 중...")

    try:
        # 1. 기존 데이터 조회 (벡터 포함)
        results = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=10000,
            with_payload=True,
            with_vectors=True
        )

        points = results[0]
        print(f"✅ {len(points)}개 포인트 조회 완료")

        if not points:
            print("⚠️  마이그레이션할 데이터가 없습니다.")
            return

        # 2. Payload 크기 분석
        sample_point = points[0]
        old_payload = sample_point.payload
        new_payload = {
            "path": old_payload.get("path"),
            "filename": old_payload.get("filename")
        }

        print(f"\n📊 Payload 변경 사항:")
        print(f"   기존 필드: {list(old_payload.keys())}")
        print(f"   새 필드: {list(new_payload.keys())}")
        print(f"   제거된 필드: {set(old_payload.keys()) - set(new_payload.keys())}")

        # 3. Payload 최소화하여 새 포인트 생성
        print(f"\n⚙️  {len(points)}개 포인트 변환 중...")
        new_points = []

        for i, point in enumerate(points):
            if i % 100 == 0 and i > 0:
                print(f"   진행: {i}/{len(points)}")

            new_points.append(
                PointStruct(
                    id=point.id,
                    vector=point.vector,
                    payload={
                        "path": point.payload.get("path"),
                        "filename": point.payload.get("filename")
                    }
                )
            )

        print(f"✅ 변환 완료")

        # 4. 업데이트 (upsert는 기존 데이터 덮어쓰기)
        print(f"\n⬆️  Qdrant 업데이트 중...")
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=new_points
        )

        print(f"✅ {len(new_points)}개 포인트 마이그레이션 완료!")

        # 5. 검증
        print(f"\n🔍 마이그레이션 검증 중...")
        verify_result = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1,
            with_payload=True,
            with_vectors=False
        )

        if verify_result[0]:
            sample = verify_result[0][0]
            print(f"✅ 검증 성공")
            print(f"   샘플 payload: {sample.payload}")

            # 예상 크기 계산
            total_docs = len(points)
            old_size_per_doc = 11.5  # KB (평균)
            new_size_per_doc = 6.2   # KB (평균)

            old_total_mb = (total_docs * old_size_per_doc) / 1024
            new_total_mb = (total_docs * new_size_per_doc) / 1024
            saved_mb = old_total_mb - new_total_mb
            saved_percent = (saved_mb / old_total_mb) * 100

            print(f"\n💾 예상 저장 공간:")
            print(f"   기존: {old_total_mb:.2f} MB")
            print(f"   변경 후: {new_total_mb:.2f} MB")
            print(f"   절감: {saved_mb:.2f} MB ({saved_percent:.1f}%)")

    except Exception as e:
        print(f"❌ 마이그레이션 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Qdrant Payload 마이그레이션")
    print("=" * 70)
    print()
    print("⚠️  주의: 이 작업은 기존 Qdrant 데이터의 payload를 변경합니다.")
    print("         text, tags, mtime, hash 필드가 제거됩니다.")
    print("         (벡터와 path, filename은 유지)")
    print()

    response = input("계속하시겠습니까? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        print()
        migrate_qdrant_payload()
        print()
        print("=" * 70)
        print("✅ 마이그레이션 완료!")
        print("=" * 70)
    else:
        print("취소되었습니다.")
