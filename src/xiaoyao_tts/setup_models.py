from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import DEFAULT_ASR_MODEL_ID, DEFAULT_DENOISER_MODEL_ID, DEFAULT_MODEL_ID
from .errors import BackendError


@dataclass
class ModelCacheStatus:
    name: str
    model_id: str
    cached: bool
    path: str | None
    size_bytes: int
    size_human: str


def human_size(size: int) -> str:
    value = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)}B"
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}TB"


def dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    seen: set[tuple[int, int]] = set()
    for item in path.rglob("*"):
        if item.is_file():
            try:
                stat = item.stat()
            except OSError:
                continue
            key = (stat.st_dev, stat.st_ino)
            if key in seen:
                continue
            seen.add(key)
            total += stat.st_size
    return total


def hf_cache_dir(model_id: str = DEFAULT_MODEL_ID) -> Path:
    base = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    return base / "hub" / f"models--{model_id.replace('/', '--')}"


def modelscope_cache_dir(model_id: str) -> Path:
    base = Path(os.environ.get("MODELSCOPE_CACHE", Path.home() / ".cache" / "modelscope" / "hub"))
    return base / "models" / model_id


def cache_status() -> list[ModelCacheStatus]:
    items = [
        ("voxcpm2", DEFAULT_MODEL_ID, hf_cache_dir(DEFAULT_MODEL_ID)),
        ("sensevoice", DEFAULT_ASR_MODEL_ID, modelscope_cache_dir(DEFAULT_ASR_MODEL_ID)),
        ("zipenhancer", DEFAULT_DENOISER_MODEL_ID, modelscope_cache_dir(DEFAULT_DENOISER_MODEL_ID)),
    ]
    statuses = []
    for name, model_id, path in items:
        size = dir_size(path)
        statuses.append(
            ModelCacheStatus(
                name=name,
                model_id=model_id,
                cached=path.exists() and size > 0,
                path=str(path) if path.exists() else None,
                size_bytes=size,
                size_human=human_size(size),
            )
        )
    return statuses


def download_voxcpm2(model_id: str = DEFAULT_MODEL_ID) -> ModelCacheStatus:
    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:  # pragma: no cover - runtime dependency path
        raise BackendError("huggingface_hub is required to download VoxCPM2. Install with .[tts] or .[all].") from exc
    path = snapshot_download(model_id)
    size = dir_size(hf_cache_dir(model_id))
    return ModelCacheStatus("voxcpm2", model_id, True, path, size, human_size(size))


def download_modelscope_model(name: str, model_id: str) -> ModelCacheStatus:
    try:
        from modelscope import snapshot_download
    except Exception as exc:  # pragma: no cover - runtime dependency path
        raise BackendError("modelscope is required to download ModelScope models. Install with .[tts] or .[all].") from exc
    path = snapshot_download(model_id)
    cache_path = modelscope_cache_dir(model_id)
    size = dir_size(cache_path)
    return ModelCacheStatus(name, model_id, True, str(path), size, human_size(size))


def download_models(*, include_asr: bool = True, include_denoiser: bool = False) -> list[ModelCacheStatus]:
    if not shutil.which("ffmpeg"):
        raise BackendError("ffmpeg is required before downloading runtime models.")
    statuses = [download_voxcpm2(DEFAULT_MODEL_ID)]
    if include_asr:
        statuses.append(download_modelscope_model("sensevoice", DEFAULT_ASR_MODEL_ID))
    if include_denoiser:
        statuses.append(download_modelscope_model("zipenhancer", DEFAULT_DENOISER_MODEL_ID))
    return statuses


def status_as_dicts() -> list[dict]:
    return [asdict(status) for status in cache_status()]
