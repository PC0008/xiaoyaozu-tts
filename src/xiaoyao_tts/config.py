from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "xiaoyaozu-tts"
DEFAULT_MODEL_ID = "openbmb/VoxCPM2"
DEFAULT_ASR_MODEL_ID = "iic/SenseVoiceSmall"
DEFAULT_DENOISER_MODEL_ID = "iic/speech_zipenhancer_ans_multiloss_16k_base"
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


def history_dir() -> Path:
    return app_home() / "history"


def history_file() -> Path:
    return history_dir() / "generations.jsonl"


def ensure_app_dirs() -> None:
    profiles_dir().mkdir(parents=True, exist_ok=True)
    outputs_dir().mkdir(parents=True, exist_ok=True)
    history_dir().mkdir(parents=True, exist_ok=True)
