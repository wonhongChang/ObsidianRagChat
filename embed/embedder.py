from openai import OpenAI
from dotenv import load_dotenv
from functools import lru_cache
import os

EMBEDDING_MODEL = "text-embedding-3-small"


def embedding_client(**options):
    load_dotenv()
    key = os.getenv("OPENAI_EMBEDDING_API_KEY", "").strip()
    if not key:
        raise ValueError("Hybrid retrieval requires OPENAI_EMBEDDING_API_KEY")
    return OpenAI(api_key=key, **options)


@lru_cache(maxsize=1)
def _runtime_client():
    return embedding_client()

def embed_texts(texts):
    """
    텍스트 리스트를 임베딩으로 변환.
    빈 텍스트가 있어도 결과 배열 길이는 항상 입력과 동일 (None으로 채움).
    """
    result = [None] * len(texts)
    batch_size = 100

    print(f"총 {len(texts)}개의 텍스트를 임베딩합니다...")

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        # Track original indices so embeddings map back correctly even if some texts are empty
        valid_indices = []
        processed_batch = []
        for j, text in enumerate(batch):
            stripped = text.strip() if isinstance(text, str) else str(text).strip()
            if stripped:
                valid_indices.append(j)
                processed_batch.append(stripped)

        if not processed_batch:
            print(f"배치 {i//batch_size + 1}: 처리할 텍스트가 없습니다.")
            continue

        print(f"배치 {i//batch_size + 1}: {len(processed_batch)}개 텍스트 처리 중...")
        response = _runtime_client().embeddings.create(input=processed_batch, model=EMBEDDING_MODEL)
        indices = [item.index for item in response.data]
        if sorted(indices) != list(range(len(processed_batch))):
            raise ValueError("Incomplete embedding response")
        for item in response.data:
            result[i + valid_indices[item.index]] = item.embedding

    return result
