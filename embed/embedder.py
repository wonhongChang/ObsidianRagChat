from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def embed_texts(texts):
    """
    텍스트 리스트를 임베딩으로 변환
    OpenAI API는 한 번에 최대 2048개의 입력을 받을 수 있음
    """
    embeddings = []
    batch_size = 100  # 한 번에 처리할 텍스트 개수
    
    print(f"총 {len(texts)}개의 텍스트를 임베딩합니다...")
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        # 각 텍스트가 문자열인지 확인하고, 너무 길면 잘라냄
        processed_batch = []
        for text in batch:
            if isinstance(text, str):
                if text.strip():
                    processed_batch.append(text.strip())
            else:
                text_str = str(text).strip()
                if text_str:
                    processed_batch.append(text_str)
        
        if not processed_batch:
            print(f"배치 {i//batch_size + 1}: 처리할 텍스트가 없습니다.")
            continue
            
        print(f"배치 {i//batch_size + 1}: {len(processed_batch)}개 텍스트 처리 중...")
        print(f"첫 번째 텍스트 샘플 (처음 100자): {processed_batch[0][:100]}")
        
        response = client.embeddings.create(
            input=processed_batch,
            model="text-embedding-3-small"
        )
        embeddings.extend([item.embedding for item in response.data])
    
    return embeddings
