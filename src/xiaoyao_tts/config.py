from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "xiaoyaozu-tts"
DEFAULT_MODEL_ID = "openbmb/VoxCPM2"
DEFAULT_SAMPLE_RATE = 16_000


def app_home() -> Path:
    value = os.environ.get("XIAOYAO_TTS_HOME")
    if value:
        return Path(value).expanduser().resolve()
    return Path.home() / ".xiaoyaozu-tts"


def profiles_dir() -> Path:
    return app_home() / "profiles"


def outputs_dir() -> Path:
    return app_home() / "outputs"


def ensure_app_dirs() -> None:
    profiles_dir().mkdir(parents=True, exist_ok=True)
    outputs_dir().mkdir(parents=True, exist_ok=True)
