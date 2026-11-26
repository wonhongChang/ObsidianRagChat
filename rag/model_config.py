import os
from typing import Literal


ChatModel = Literal["gpt-6-luna"]
CHAT_MODEL: ChatModel = "gpt-6-luna"


def retrieval_mode() -> Literal["lexical", "hybrid"]:
    return "hybrid" if os.getenv("OPENAI_EMBEDDING_API_KEY", "").strip() else "lexical"
