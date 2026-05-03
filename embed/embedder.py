from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        print(f"첫 번째 텍스트 샘플 (처음 100자): {processed_batch[0][:100]}")

        response = client.embeddings.create(
            input=processed_batch,
            model="text-embedding-3-small"
        )

        for k, item in enumerate(response.data):
            result[i + valid_indices[k]] = item.embedding

    return result
