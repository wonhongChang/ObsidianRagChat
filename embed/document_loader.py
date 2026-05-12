import os
from dotenv import load_dotenv
import re
import hashlib

load_dotenv()
VAULT_PATH = os.getenv("VAULT_PATH")

def extract_tags(content):
    """
    마크다운 파일의 상단 태그 블록에서 태그 추출 (#태그 형식)
    빈 줄 또는 마크다운 제목(# 제목)이 나올 때까지 모든 태그 추출
    """
    lines = content.split('\n')
    if not lines:
        return []

    tags = []
    for line in lines:
        line = line.strip()

        # 빈 줄이면 태그 블록 끝
        if not line:
            break

        # 마크다운 제목(# 제목, ## 제목 등)이 나오면 태그 블록 끝
        if re.match(r'^#{1,6}\s+', line):
            break

        # 이 줄에서 태그 추출
        line_tags = re.findall(r'#(\w+)', line)
        tags.extend(line_tags)

    return list(set(tags))  # 중복 제거

def get_file_hash(content):
    """파일 내용의 해시값 계산"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def load_markdown_files(vault_path: str = VAULT_PATH):
    """
    마크다운 파일을 로드하고 메타데이터와 함께 반환
    Returns:
        list: [{"text": str, "filename": str, "path": str, "tags": list, "mtime": float, "hash": str}, ...]
    """
    if not vault_path:
        raise ValueError("VAULT_PATH 환경변수가 설정되지 않았습니다.")
    if not os.path.isdir(vault_path):
        raise FileNotFoundError(f"Obsidian vault 경로를 찾을 수 없습니다: {vault_path}")

    documents = []
    for root, _, files in os.walk(vault_path):
        for f in files:
            if f.endswith(".md"):
                file_path = os.path.join(root, f)
                relative_path = os.path.relpath(file_path, vault_path)
                
                try:
                    # 파일 수정 시간
                    mtime = os.path.getmtime(file_path)
                    
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()
                        
                        # 빈 파일 제외
                        if not content.strip():
                            continue
                        
                        tags = extract_tags(content)
                        file_hash = get_file_hash(content)
                        
                        documents.append({
                            "text": content,
                            "filename": f,
                            "path": relative_path,
                            "tags": tags,
                            "mtime": mtime,
                            "hash": file_hash
                        })
                except Exception as e:
                    print(f"⚠️  파일 읽기 실패 ({f}): {e}")
                    continue
    
    print(f"✅ {len(documents)}개의 마크다운 파일을 로드했습니다.")
    return documents
