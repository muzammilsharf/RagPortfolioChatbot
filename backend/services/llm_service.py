from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, Iterator

from services.prompt import get_system_prompt
from groq import Groq
from google import genai
from google.genai import errors as genai_errors

from core import settings
from services.memory_service import Turn
from services.retrieval import RetrievedChunk


SYSTEM_PROMPT = get_system_prompt()

@dataclass(frozen=True)
class Candidate:
    provider: str
    model: str


_cooldown_until: dict[tuple[str, str], float] = {}
_ema_ttft_s: dict[tuple[str, str], float] = {}


def _parse_candidates(raw: str) -> list[Candidate]:
    raw = (raw or "").strip()
    if not raw:
        return []
    out: list[Candidate] = []
    for part in raw.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        prov, model = part.split(":", 1)
        prov = prov.strip().lower()
        model = model.strip()
        if prov and model:
            out.append(Candidate(provider=prov, model=model))
    return out


def _now() -> float:
    return time.monotonic()


def _format_context(chunks: list[RetrievedChunk]) -> str:
    lines: list[str] = []
    for idx, ch in enumerate(chunks, start=1):
        src = f" (source: {ch.source})" if ch.source else ""
        text = ch.text
        if settings.max_chunk_chars and len(text) > settings.max_chunk_chars:
            text = text[: settings.max_chunk_chars].rstrip() + "\n…"
        lines.append(f"[{idx}]{src}\n{text}")
    return "\n\n".join(lines).strip()


def _messages(*, history: list[Turn], user_message: str, context: str) -> list[dict]:
    msgs: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"CONTEXT:\n{context if context else '(empty)'}"},
    ]
    for t in history:
        if t.role in ("user", "assistant"):
            msgs.append({"role": t.role, "content": t.content})
    msgs.append({"role": "user", "content": user_message})
    return msgs


def _gemini_prompt(*, history: list[Turn], user_message: str, context: str) -> str:
    # Gemini accepts free-form text well for this use-case; keep it simple and grounded.
    parts: list[str] = [
        SYSTEM_PROMPT.strip(),
        "",
        "CONTEXT:",
        context.strip() if context else "(empty)",
        "",
        "CHAT HISTORY:",
    ]
    for t in history:
        if t.role in ("user", "assistant"):
            parts.append(f"{t.role.upper()}: {t.content}")
    parts.append("")
    parts.append(f"USER: {user_message}")
    parts.append("ASSISTANT:")
    return "\n".join(parts).strip()


class LlmService:
    def __init__(self) -> None:
        raw = (settings.llm_provider or "groq").strip().lower()
        # Accept common aliases/typos to avoid hard failures from env config.
        alias_map = {
            "grok": "groq",
            "groqai": "groq",
            "google": "gemini",
            "google-genai": "gemini",
            "genai": "gemini",
        }
        self._provider = alias_map.get(raw, raw)
        # Create clients lazily so a multi-candidate pool can work even if one provider is not configured.
        self._groq = None
        self._gemini = None
        if self._provider not in ("groq", "gemini"):
            raise RuntimeError(f"I'm trying to speak a language I haven't learned yet! Please stick to my primary tutors: {settings.llm_provider} (use groq|gemini)")

    def _ensure_client(self, provider: str) -> None:
        if provider == "groq":
            if not self._groq:
                if not settings.groq_api_key:
                    raise RuntimeError("I’ve forgotten how to think! My brain (API) isn't connected. I'll be back as soon as I find my spark.")
                self._groq = Groq(api_key=settings.groq_api_key)
        elif provider == "gemini":
            if not self._gemini:
                if not settings.gemini_api_key:
                    raise RuntimeError("I’ve forgotten how to think! My brain (API) isn't connected. I'll be back as soon as I find my spark.")
                self._gemini = genai.Client(api_key=settings.gemini_api_key)
        else:
            raise RuntimeError(f"I'm trying to speak a language I haven't learned yet! {provider}")

    def _stream_groq(self, *, model: str, msgs: list[dict]) -> Iterator[str]:
        self._ensure_client("groq")
        stream = self._groq.chat.completions.create(
            model=model,
            messages=msgs,
            temperature=0.3,
            max_tokens=settings.groq_max_tokens,
            stream=True,
        )
        for event in stream:
            delta = event.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content

    def _stream_gemini(self, *, model: str, prompt: str) -> Iterator[str]:
        self._ensure_client("gemini")
        stream = self._gemini.models.generate_content_stream(model=model, contents=prompt)
        for chunk in stream:
            text = getattr(chunk, "text", None)
            if text:
                yield text

    def stream_answer(
        self,
        *,
        history: list[Turn],
        user_message: str,
        retrieved: list[RetrievedChunk],
    ) -> Iterable[str]:
        context = _format_context(retrieved)
        msgs = _messages(history=history, user_message=user_message, context=context)
        prompt = _gemini_prompt(history=history, user_message=user_message, context=context)

        # 1) If a candidate pool is configured, route across it automatically.
        candidates = _parse_candidates(settings.llm_candidates)

        # 2) Otherwise, keep existing behavior but express it as candidates.
        if not candidates:
            if self._provider == "gemini":
                candidates = [Candidate("gemini", settings.gemini_model)]
                if settings.gemini_fallback_model:
                    candidates.append(Candidate("gemini", settings.gemini_fallback_model))
            else:
                candidates = [Candidate("groq", settings.groq_model)]
                if settings.allow_provider_fallback and settings.gemini_api_key:
                    candidates.append(Candidate("gemini", settings.gemini_model))

        now = _now()

        def sort_key(c: Candidate) -> tuple[bool, float]:
            cd = _cooldown_until.get((c.provider, c.model), 0.0)
            in_cd = cd > now
            ema = _ema_ttft_s.get((c.provider, c.model), 9.9)
            return (in_cd, ema)

        candidates.sort(key=sort_key)

        last_err: Exception | None = None
        for cand in candidates:
            k = (cand.provider, cand.model)
            if _cooldown_until.get(k, 0.0) > _now():
                continue

            t0 = _now()
            first = True
            try:
                if cand.provider == "groq":
                    stream = self._stream_groq(model=cand.model, msgs=msgs)
                elif cand.provider == "gemini":
                    stream = self._stream_gemini(model=cand.model, prompt=prompt)
                else:
                    raise RuntimeError(f"I’m a bit confused! I’ve been asked to use a tool I don’t have in my backpack: {cand.provider}")

                for tok in stream:
                    if first:
                        first = False
                        ttft = _now() - t0
                        prev = _ema_ttft_s.get(k)
                        _ema_ttft_s[k] = ttft if prev is None else (0.7 * prev + 0.3 * ttft)
                        if ttft > settings.llm_first_token_timeout_seconds:
                            _cooldown_until[k] = _now() + settings.llm_cooldown_seconds
                            raise TimeoutError(f"First token too slow from {cand.provider}:{cand.model}")
                    yield tok
                return

            except genai_errors.ServerError as e:
                _cooldown_until[k] = _now() + settings.llm_cooldown_seconds
                last_err = e
                continue
            except Exception as e:
                msg = str(e).lower()
                is_429 = ("429" in msg) or ("rate_limit" in msg) or ("rate limit" in msg)
                if is_429 or isinstance(e, TimeoutError):
                    _cooldown_until[k] = _now() + settings.llm_cooldown_seconds
                last_err = e
                continue

        raise RuntimeError("All my AI systems are currently resting") from last_err
