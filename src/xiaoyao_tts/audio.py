from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .config import DEFAULT_SAMPLE_RATE
from .errors import AudioToolError


def find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise AudioToolError("ffmpeg is required. Install ffmpeg and make sure it is on PATH.")
    return path


def find_ffprobe() -> str | None:
    return shutil.which("ffprobe")


def convert_to_reference_wav(source: Path, target: Path, sample_rate: int = DEFAULT_SAMPLE_RATE) -> Path:
    if not source.exists():
        raise AudioToolError(f"Audio file does not exist: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-sample_fmt",
        "s16",
        str(target),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        message = result.stderr.strip() or "Failed to convert audio with ffmpeg."
        raise AudioToolError(message)
    return target


def change_audio_speed(source: Path, target: Path, speed: float) -> Path:
    if not source.exists():
        raise AudioToolError(f"Audio file does not exist: {source}")
    if not 0.5 <= speed <= 2.0:
        raise AudioToolError("Speed must be between 0.5 and 2.0.")
    target.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-filter:a",
        f"atempo={speed:.3f}",
        "-ac",
        "1",
        "-sample_fmt",
        "s16",
        str(target),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        message = result.stderr.strip() or "Failed to change audio speed with ffmpeg."
        raise AudioToolError(message)
    return target


def audio_info(path: Path) -> dict:
    if not path.exists():
        raise AudioToolError(f"Audio file does not exist: {path}")
    ffprobe = find_ffprobe()
    if not ffprobe:
        return {"path": str(path)}
    command = [
        ffprobe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return {"path": str(path), "probe_error": result.stderr.strip()}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"path": str(path)}
    audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})
    fmt = data.get("format", {})
    duration = audio_stream.get("duration") or fmt.get("duration")
    return {
        "path": str(path),
        "codec": audio_stream.get("codec_name"),
        "sample_rate": int(audio_stream["sample_rate"]) if audio_stream.get("sample_rate") else None,
        "channels": audio_stream.get("channels"),
        "duration_sec": float(duration) if duration else None,
        "format": fmt.get("format_name"),
    }
