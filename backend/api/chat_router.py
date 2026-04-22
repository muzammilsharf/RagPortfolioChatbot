from __future__ import annotations

import json
from typing import Iterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import anyio
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from core import settings
from services import ChromaVectorStoreRepository, LlmService, MemoryService, Turn, embed_query


router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

_memory = MemoryService(max_turns=settings.memory_turns)
_repo = ChromaVectorStoreRepository()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(min_length=8, max_length=128)


def _sse(data: dict, event: str | None = None) -> str:
    lines: list[str] = []
    if event:
        lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    return "\n".join(lines) + "\n\n"


def _sanitize_user_message(msg: str) -> str:
    # Basic prompt-injection hardening: keep plain text, cap size, collapse weird whitespace.
    msg = msg.replace("\x00", " ").strip()
    if len(msg) > 4000:
        msg = msg[:4000]
    return msg


@router.post("/api/v1/chat")
@limiter.limit(lambda: f"{settings.rate_limit_per_minute}/minute")
async def chat(request: Request, payload: ChatRequest) -> StreamingResponse:
    user_message = _sanitize_user_message(payload.message)
    session_id = payload.session_id

    history = _memory.get_history(session_id)

    # Heuristic query expansion: helps when user types very short prompts like "projects".
    expanded = user_message
    if len(user_message.split()) <= 3:
        expanded = f"{user_message}\n\nresume projects experience skills tech stack education"

    # Embedding + retrieval are CPU/IO bound; run in worker thread to reduce event-loop blocking.
    query_emb = await anyio.to_thread.run_sync(embed_query, expanded)
    retrieved = await anyio.to_thread.run_sync(
        lambda: _repo.hybrid_search(
            query_text=user_message,
            query_embedding=query_emb,
            top_k=settings.top_k,
            candidate_k=settings.hybrid_candidate_k,
            vector_weight=settings.hybrid_vector_weight,
            keyword_weight=settings.hybrid_keyword_weight,
        )
    )
    best_score = retrieved[0].score if retrieved else 0.0
    weak_context = best_score < settings.min_similarity
    context_chunks = retrieved[: max(3, min(settings.top_k, settings.max_context_chunks))]

    llm = LlmService()

    def gen() -> Iterator[str]:
        yield _sse(
            {
                "type": "meta",
                "retrieved": len(context_chunks),
                "weak_context": weak_context,
                "best_score": best_score,
                "sources": [{"source": c.source, "score": c.score} for c in context_chunks],
            },
            event="meta",
        )
        collected: list[str] = []
        try:
            for token in llm.stream_answer(history=history, user_message=user_message, retrieved=context_chunks):
                collected.append(token)
                yield _sse({"type": "token", "text": token}, event="token")
            answer = "".join(collected).strip()
            yield _sse({"type": "done"}, event="done")

            _memory.append(session_id, Turn(role="user", content=user_message))
            _memory.append(session_id, Turn(role="assistant", content=answer))
        except Exception as e:
            # Don't crash the SSE stream; surface a clean message to UI.
            yield _sse({"type": "error", "message": str(e)}, event="error")
            yield _sse({"type": "done"}, event="done")

    return StreamingResponse(gen(), media_type="text/event-stream")
