# Copilot Instructions for ObsidianQudrantDualBrain

> Repository custom instructions for GitHub Copilot to understand the project structure, build requirements, and coding guidelines.

## Project Overview

This project is an Obsidian RAG (Retrieval-Augmented Generation) Chat system that converts Obsidian notes into a searchable knowledge base using vector embeddings and provides AI-powered Q&A through a web interface.

**Technology Stack:**
- Backend: Python 3.13, FastAPI
- Vector DB: Qdrant Cloud (1GB free tier)
- LLM: OpenAI GPT-4o-mini (primary), GPT-5-mini (reasoning model)
- Embedding: OpenAI text-embedding-3-small (1536-dim)
- Token Counting: tiktoken (cl100k_base)
- Frontend: Vanilla JavaScript

## Project Structure

```
ObsidianQudrantSync/
├── .github/
│   └── copilot-instructions.md    # This file - Copilot configuration
├── embed/                          # Embedding modules
│   ├── embedder.py                 # OpenAI embedding generation
│   ├── loader.py                   # Obsidian markdown file loader
│   └── qdrant_client.py            # Qdrant vector DB client
├── search/                         # Search modules
│   └── searcher.py                 # Vector search utilities
├── rag/                            # RAG system core
│   └── gpt_rag.py                  # RAG logic with dual API support
├── api/                            # API endpoints
│   └── endpoints.py                # FastAPI router definitions
├── templates/                      # HTML templates
│   └── chat.html                   # Web chat interface
├── static/                         # Static assets
├── main.py                         # DB upload/sync script
├── app.py                          # FastAPI web server entry point
├── requirements.txt                # Python dependencies
└── .env                            # Environment variables (DO NOT commit)
```

## Build & Run Instructions

### Prerequisites
- Python 3.13+
- OpenAI API key
- Qdrant Cloud account (free tier)
- Obsidian vault with markdown files

### Environment Setup

1. **Create virtual environment** (always required first):
   ```bash
   python -m venv venv
   ```

2. **Activate virtual environment**:
   ```powershell
   # Windows PowerShell
   venv\Scripts\activate
   
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables** in `.env`:
   ```env
   OPENAI_API_KEY=sk-your-openai-api-key
   QDRANT_URL=https://your-cluster.cloud.qdrant.io:6333
   QDRANT_API_KEY=your-qdrant-api-key
   OBSIDIAN_VAULT_PATH=C:/path/to/your/obsidian/vault
   ```

### Build Steps

**Initial Setup (first time only):**
```bash
# Upload all notes to Qdrant
python main.py --full
```

**Incremental Updates (when notes change):**
```bash
# Only upload changed/new notes
python main.py
```

**Start Web Server:**
```bash
python app.py
# Server runs at http://localhost:8000
```

### Testing

**Manual Testing:**
1. Open http://localhost:8000 in browser
2. Test query: "일본어 학습 방법 알려줘"
3. Verify response and sources

**Check Logs:**
```powershell
# View recent logs
Get-Content rag_query.log -Tail 50

# Real-time monitoring
Get-Content rag_query.log -Wait
```

## Architecture & Key Concepts

### Dual API Pattern (CRITICAL)

This project supports two OpenAI API types with different response structures:

**Chat Completions API** (GPT-4o-mini):
```python
response = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[...],
    max_tokens=800,
    temperature=0.7
)
answer = response.choices[0].message.content
usage = response.usage  # prompt_tokens, completion_tokens
```

**Responses API** (GPT-5-mini):
```python
response = openai_client.responses.create(
    model="gpt-5-mini",
    reasoning={"effort": "medium"},
    input=[...],  # NOT messages
    max_output_tokens=4000  # NOT max_tokens
)
answer = response.output_text  # NOT choices[].message.content
usage = response.usage  # input_tokens, output_tokens, reasoning_tokens
```

**Implementation Pattern in `rag/gpt_rag.py`:**
```python
if model == "gpt-5-mini":
    # Use Responses API
    response = openai_client.responses.create(...)
    answer = response.output_text
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
else:
    # Use Chat Completions API
    response = openai_client.chat.completions.create(...)
    answer = response.choices[0].message.content
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
```

### RAG Pipeline

1. **Embedding** (`embed/embedder.py`):
   - Batch processing (100 texts/request)
   - Rate limit handling (3 RPM for free tier)
   - Token counting with tiktoken

2. **Vector Search** (`search/searcher.py`):
   - Cosine similarity search in Qdrant
   - Tag filtering support (#painpoint, #idea)
   - ZD document exclusion (case-insensitive)

3. **Context Assembly** (`rag/gpt_rag.py`):
   - Auto mode: 110K tokens (GPT-4o-mini), 180K tokens (GPT-5-mini)
   - Manual mode: User-specified note count
   - Token limit enforcement

4. **Answer Generation**:
   - System prompt with Korean response requirement
   - Source attribution (file names)
   - Cost calculation and logging

## Coding Guidelines

### 1. Logging (MANDATORY)

Use Korean logs with emojis for all major operations:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("✅ 작업 성공")
logger.warning("⚠️ 경고 메시지")
logger.error("❌ 에러 발생")
logger.info(f"💰 비용: ${cost:.6f}")
logger.info(f"📊 토큰: {tokens}")
```

### 2. API Response Structure

All API endpoints return consistent JSON:

```python
{
    "answer": "답변 내용",
    "sources": ["file1.md", "file2.md"],
    "usage": {
        "input_tokens": 1000,
        "output_tokens": 500,
        "total_tokens": 1500
    },
    "cost": 0.015,
    "notes_used": 50
}
```

### 3. Error Handling

Always use try-except with user-friendly messages:

```python
try:
    result = await some_operation()
except Exception as e:
    logger.error(f"❌ 작업 실패: {str(e)}")
    raise HTTPException(
        status_code=500,
        detail="작업 처리 중 오류가 발생했습니다."
    )
```

### 4. Model Selection Logic

**Always check model type** before API calls:

```python
if model == "gpt-5-mini":
    # Responses API with specific parameters
    # max_output_tokens >= 4000 (reasoning + answer)
    # reasoning effort: low/medium/high
else:
    # Chat Completions API
    # max_tokens, temperature customizable
```

### 5. Cost Calculation

Model pricing (per 1M tokens):

```python
# GPT-4o-mini
INPUT_PRICE = 0.15   # $0.15 per 1M input tokens
OUTPUT_PRICE = 0.60  # $0.60 per 1M output tokens

# GPT-5-mini  
INPUT_PRICE = 0.25   # $0.25 per 1M input tokens
OUTPUT_PRICE = 2.00  # $2.00 per 1M output tokens (includes reasoning)

# Calculate
input_cost = (input_tokens / 1_000_000) * INPUT_PRICE
output_cost = (output_tokens / 1_000_000) * OUTPUT_PRICE
total_cost = input_cost + output_cost
```

## Common Pitfalls & Solutions

### Issue 1: GPT-5-mini Empty Response
**Symptom**: `message.content` is empty, 800 reasoning_tokens used  
**Cause**: Using Chat Completions API instead of Responses API  
**Solution**: Use `openai_client.responses.create()` with `max_output_tokens=4000+`

### Issue 2: Token Limit Exceeded
**Symptom**: 429 error or incomplete responses  
**Solution**: Reduce note count or use ZD filtering (359 → 182 notes)

### Issue 3: ZD Filtering Not Working
**Symptom**: Technical docs still included  
**Solution**: Ensure case-insensitive matching: `filename.lower().startswith('zd')`

### Issue 4: Embedding Rate Limits
**Symptom**: 429 error during batch upload  
**Solution**: Built-in rate limiting (wait 20 seconds between batches)

## Environment Variables

Required in `.env` (never commit this file):

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-...              # Required for embeddings and LLM

# Qdrant Configuration  
QDRANT_URL=https://...             # Qdrant cluster URL
QDRANT_API_KEY=...                 # Qdrant API key

# Obsidian Vault
OBSIDIAN_VAULT_PATH=...            # Full path to vault root
```

## Testing Checklist

Before committing code changes:

- [ ] Activate virtual environment
- [ ] Run `python main.py` (incremental update)
- [ ] Start `python app.py`
- [ ] Test query in browser at http://localhost:8000
- [ ] Check `rag_query.log` for errors
- [ ] Verify cost calculation in logs
- [ ] Test both GPT-4o-mini and GPT-5-mini models
- [ ] Verify ZD filtering if enabled

## Key Files to Understand

- **`rag/gpt_rag.py`**: Core RAG logic with dual API support (lines 265-685)
- **`embed/embedder.py`**: OpenAI embedding generation with batching
- **`search/searcher.py`**: Qdrant vector search with filtering
- **`app.py`**: FastAPI server with `/api/search` endpoint
- **`templates/chat.html`**: Web UI with model selection and controls

## Additional Notes

- **Korean Language**: All user-facing text and logs use Korean
- **Token Counting**: Use tiktoken with `cl100k_base` encoding
- **Markdown Processing**: Preserve frontmatter and structure
- **Cost Monitoring**: Log all API usage and costs
- **Rate Limiting**: Handle OpenAI free tier limits (3 RPM embeddings)

---

**Last Updated**: 2025-11-02  
**Project**: ObsidianQudrantDualBrain  
**Maintainer**: Jake-KIM

## Common Pitfalls & Solutions

### Issue 1: GPT-5-mini Empty Response
**Symptom**: `message.content` is empty, 800 reasoning_tokens used  
**Cause**: Using Chat Completions API instead of Responses API  
**Solution**: Use `openai_client.responses.create()` with `max_output_tokens=4000+`

### Issue 2: Token Limit Exceeded
**Symptom**: 429 error or incomplete responses  
**Solution**: Reduce note count or use ZD filtering (359 → 182 notes)

### Issue 3: ZD Filtering Not Working
**Symptom**: Technical docs still included  
**Solution**: Ensure case-insensitive matching: `filename.lower().startswith('zd')`

### Issue 4: Embedding Rate Limits
**Symptom**: 429 error during batch upload  
**Solution**: Built-in rate limiting (wait 20 seconds between batches)

## Environment Variables

Required in `.env` (never commit this file):

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-...              # Required for embeddings and LLM

# Qdrant Configuration  
QDRANT_URL=https://...             # Qdrant cluster URL
QDRANT_API_KEY=...                 # Qdrant API key

# Obsidian Vault
OBSIDIAN_VAULT_PATH=...            # Full path to vault root
```

## Testing Checklist

Before committing code changes:

- [ ] Activate virtual environment
- [ ] Run `python main.py` (incremental update)
- [ ] Start `python app.py`
- [ ] Test query in browser at http://localhost:8000
- [ ] Check `rag_query.log` for errors
- [ ] Verify cost calculation in logs
- [ ] Test both GPT-4o-mini and GPT-5-mini models
- [ ] Verify ZD filtering if enabled

## Key Files to Understand

- **`rag/gpt_rag.py`**: Core RAG logic with dual API support (lines 265-685)
- **`embed/embedder.py`**: OpenAI embedding generation with batching
- **`search/searcher.py`**: Qdrant vector search with filtering
- **`app.py`**: FastAPI server with `/api/search` endpoint
- **`templates/chat.html`**: Web UI with model selection and controls

## Additional Notes

- **Korean Language**: All user-facing text and logs use Korean
- **Token Counting**: Use tiktoken with `cl100k_base` encoding
- **Markdown Processing**: Preserve frontmatter and structure
- **Cost Monitoring**: Log all API usage and costs
- **Rate Limiting**: Handle OpenAI free tier limits (3 RPM embeddings)

---

**Last Updated**: 2025-11-02  
**Project**: ObsidianQudrantDualBrain  
**Maintainer**: Jake-KIM
