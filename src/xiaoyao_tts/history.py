from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import ensure_app_dirs, history_file


@dataclass
class GenerationRecord:
    id: str
    created_at: str
    profile: str
    text: str
    output: str
    sample_rate: int | None
    duration_sec: float | None
    device: str
    model: str
    cfg_value: float
    inference_timesteps: int
    source: str
    speed: float = 1.0
    batch_id: str | None = None
    item_id: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_record_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"gen-{stamp}-{uuid.uuid4().hex[:8]}"


def new_batch_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"batch-{stamp}-{uuid.uuid4().hex[:8]}"


def append_generation_record(record: GenerationRecord) -> GenerationRecord:
    ensure_app_dirs()
    path = history_file()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    return record


def record_generation(
    *,
    profile: str,
    text: str,
    output: str | Path,
    sample_rate: int | None,
    duration_sec: float | None,
    device: str,
    model: str,
    cfg_value: float,
    inference_timesteps: int,
    source: str,
    speed: float = 1.0,
    batch_id: str | None = None,
    item_id: str | None = None,
) -> GenerationRecord:
    return append_generation_record(
        GenerationRecord(
            id=new_record_id(),
            created_at=utc_now(),
            profile=profile,
            text=text,
            output=str(Path(output).expanduser().resolve()),
            sample_rate=sample_rate,
            duration_sec=duration_sec,
            device=device,
            model=model,
            cfg_value=cfg_value,
            inference_timesteps=inference_timesteps,
            source=source,
            speed=speed,
            batch_id=batch_id,
            item_id=item_id,
        )
    )


def list_generation_records(limit: int = 20, profile: str | None = None) -> list[GenerationRecord]:
    ensure_app_dirs()
    path = history_file()
    if not path.exists():
        return []
    records: list[GenerationRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        payload.setdefault("speed", 1.0)
        if profile and payload.get("profile") != profile:
            continue
        records.append(GenerationRecord(**payload))
    records.reverse()
    return records[:limit]
