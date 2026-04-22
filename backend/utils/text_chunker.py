from __future__ import annotations

from dataclasses import dataclass

import tiktoken


@dataclass(frozen=True)
class Chunk:
    text: str
    start_token: int
    end_token: int


def _normalize(text: str) -> str:
    # Keep paragraph breaks, normalize whitespace inside lines.
    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.strip() for ln in text.split("\n")]
    # Preserve blank lines as paragraph separators
    out: list[str] = []
    blank = False
    for ln in lines:
        if not ln:
            if not blank:
                out.append("")
            blank = True
            continue
        blank = False
        out.append(" ".join(ln.split()))
    return "\n".join(out).strip()


def chunk_text_semantic(
    text: str,
    *,
    chunk_size_tokens: int,
    chunk_overlap_tokens: int,
    encoding_name: str = "cl100k_base",
) -> list[Chunk]:
    """
    More retrieval-friendly chunking:
    - Split into paragraphs (blank-line separated) to avoid mid-thought cuts
    - Pack paragraphs into ~chunk_size_tokens windows
    - Apply token-overlap between chunks
    """
    if chunk_size_tokens <= 0:
        raise ValueError("chunk_size_tokens must be > 0")
    if chunk_overlap_tokens < 0:
        raise ValueError("chunk_overlap_tokens must be >= 0")
    if chunk_overlap_tokens >= chunk_size_tokens:
        raise ValueError("chunk_overlap_tokens must be < chunk_size_tokens")

    text = _normalize(text)
    if not text:
        return []

    enc = tiktoken.get_encoding(encoding_name)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[Chunk] = []
    cur_tokens: list[int] = []
    cur_start_token = 0
    cursor = 0  # token cursor in the virtual concatenation

    def flush() -> None:
        nonlocal cur_tokens, cur_start_token
        if not cur_tokens:
            return
        chunk_text = enc.decode(cur_tokens).strip()
        if chunk_text:
            chunks.append(Chunk(text=chunk_text, start_token=cur_start_token, end_token=cur_start_token + len(cur_tokens)))

        # overlap: keep last N tokens as seed for next chunk
        if chunk_overlap_tokens > 0:
            cur_tokens = cur_tokens[-chunk_overlap_tokens:]
            cur_start_token = (chunks[-1].end_token - len(cur_tokens)) if chunks else 0
        else:
            cur_tokens = []

    for p in paragraphs:
        p_tokens = enc.encode(p + "\n\n")

        # If a single paragraph is huge, fall back to raw token windowing for it.
        if len(p_tokens) > chunk_size_tokens:
            flush()
            # window the big paragraph
            big = enc.encode(p)
            i = 0
            while i < len(big):
                end = min(i + chunk_size_tokens, len(big))
                win = big[i:end]
                win_text = enc.decode(win).strip()
                if win_text:
                    chunks.append(Chunk(text=win_text, start_token=cursor + i, end_token=cursor + end))
                i = end - chunk_overlap_tokens
                if i < 0:
                    i = 0
                if end == len(big):
                    break
            cursor += len(big) + len(enc.encode("\n\n"))
            continue

        # If adding this paragraph would overflow, flush current chunk first.
        if cur_tokens and (len(cur_tokens) + len(p_tokens) > chunk_size_tokens):
            flush()

        if not cur_tokens:
            cur_start_token = cursor

        cur_tokens.extend(p_tokens)
        cursor += len(p_tokens)

    flush()
    return chunks


def chunk_text_tokens(
    text: str,
    *,
    chunk_size_tokens: int,
    chunk_overlap_tokens: int,
    encoding_name: str = "cl100k_base",
) -> list[Chunk]:
    if chunk_size_tokens <= 0:
        raise ValueError("chunk_size_tokens must be > 0")
    if chunk_overlap_tokens < 0:
        raise ValueError("chunk_overlap_tokens must be >= 0")
    if chunk_overlap_tokens >= chunk_size_tokens:
        raise ValueError("chunk_overlap_tokens must be < chunk_size_tokens")

    enc = tiktoken.get_encoding(encoding_name)
    tokens = enc.encode(text)
    chunks: list[Chunk] = []

    i = 0
    while i < len(tokens):
        end = min(i + chunk_size_tokens, len(tokens))
        chunk_tokens = tokens[i:end]
        chunk_text = enc.decode(chunk_tokens).strip()
        if chunk_text:
            chunks.append(Chunk(text=chunk_text, start_token=i, end_token=end))
        i = end - chunk_overlap_tokens
        if i < 0:
            i = 0
        if end == len(tokens):
            break

    return chunks
