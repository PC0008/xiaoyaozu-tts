from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SplitPreset:
    label: str
    min_chars: int
    target_chars: int
    max_chars: int


@dataclass(frozen=True)
class TextSegment:
    id: str
    text: str


SPLIT_PRESETS: dict[str, SplitPreset] = {
    "short": SplitPreset(label="紧凑短视频", min_chars=24, target_chars=32, max_chars=40),
    "standard": SplitPreset(label="自然口播", min_chars=45, target_chars=56, max_chars=70),
    "long": SplitPreset(label="长句连贯", min_chars=130, target_chars=160, max_chars=180),
}

NATURAL_BREAK_PATTERN = re.compile(r"[^。！？!?；;，,、：:.．·]+[。！？!?；;，,、：:.．·]*[\"\"'')）】》]*|[。！？!?；;，,、：:.．·]+")
FALLBACK_BREAK_PATTERN = re.compile(r"[。！？!?；;，,、：:.．·\s]")
STRONG_BREAK_PATTERN = re.compile(r"(?:[。！？!?；;.．]+|·{2,})[\"\"'')）】》]*$")
MAX_SHORT_TAIL_OVERFLOW = 20


def effective_text_length(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def ends_with_strong_break(text: str) -> bool:
    return bool(STRONG_BREAK_PATTERN.search(text.strip()))


def split_overlong_piece(piece: str, preset: SplitPreset) -> list[str]:
    chunks: list[str] = []
    rest = piece.strip()

    while len(rest) > preset.max_chars:
        window_text = rest[: preset.max_chars + 1]
        break_at = -1
        for match in FALLBACK_BREAK_PATTERN.finditer(window_text):
            if match.end() >= preset.min_chars:
                break_at = match.end()

        if break_at < 0:
            break_at = preset.target_chars

        chunk = rest[:break_at].strip()
        if chunk:
            chunks.append(chunk)
        rest = rest[break_at:].strip()

    if rest:
        chunks.append(rest)
    return chunks


def split_long_text(text: str, preset_key: str = "long") -> list[TextSegment]:
    preset = SPLIT_PRESETS[preset_key]
    normalized = re.sub(r"[ \t]+", " ", text.replace("\r", "")).strip()
    if not normalized:
        return []

    pieces: list[str] = []
    for paragraph in re.split(r"\n+", normalized):
        matches = NATURAL_BREAK_PATTERN.findall(paragraph)
        pieces.extend(matches if matches else [paragraph])
    pieces = [item.strip() for item in pieces if item.strip()]

    chunks: list[str] = []
    buffer = ""

    def flush_buffer() -> None:
        nonlocal buffer
        if buffer.strip():
            chunks.append(buffer.strip())
        buffer = ""

    def add_piece(piece: str) -> None:
        nonlocal buffer
        if not piece.strip():
            return
        if not buffer:
            buffer = piece
            return
        if len(buffer) >= preset.min_chars and ends_with_strong_break(buffer):
            flush_buffer()
            buffer = piece
            return
        if len(buffer) + len(piece) <= preset.max_chars:
            buffer = f"{buffer}{piece}"
            return
        if (
            ends_with_strong_break(piece)
            and len(piece) <= preset.target_chars // 4
            and len(buffer) + len(piece) <= preset.max_chars + MAX_SHORT_TAIL_OVERFLOW
        ):
            buffer = f"{buffer}{piece}"
            return
        flush_buffer()
        buffer = piece

    for piece in pieces:
        if len(piece) <= preset.max_chars:
            add_piece(piece)
            continue
        flush_buffer()
        chunks.extend(split_overlong_piece(piece, preset))

    flush_buffer()

    return [TextSegment(id=str(index + 1).zfill(3), text=chunk) for index, chunk in enumerate(chunks)]
