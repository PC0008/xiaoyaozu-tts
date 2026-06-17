from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .errors import XiaoyaoTTSError


@dataclass
class BatchItem:
    id: str
    text: str


def safe_item_id(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff_-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-_")
    return value or "item"


def parse_text_batch(path: Path) -> list[BatchItem]:
    items = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        items.append(BatchItem(id=f"line-{index:03d}", text=text))
    return items


def parse_jsonl_batch(path: Path) -> list[BatchItem]:
    items = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        text = str(payload.get("text", "")).strip()
        if not text:
            raise XiaoyaoTTSError(f"Missing text in JSONL line {index}.")
        item_id = safe_item_id(str(payload.get("id") or f"item-{index:03d}"))
        items.append(BatchItem(id=item_id, text=text))
    return items


def load_batch_items(path: Path, input_format: str = "auto") -> list[BatchItem]:
    if not path.exists():
        raise XiaoyaoTTSError(f"Batch input file does not exist: {path}")
    chosen = input_format
    if chosen == "auto":
        chosen = "jsonl" if path.suffix.lower() == ".jsonl" else "txt"
    if chosen == "txt":
        items = parse_text_batch(path)
    elif chosen == "jsonl":
        items = parse_jsonl_batch(path)
    else:
        raise XiaoyaoTTSError(f"Unsupported batch input format: {input_format}")
    if not items:
        raise XiaoyaoTTSError("Batch input did not contain any text items.")
    return items
