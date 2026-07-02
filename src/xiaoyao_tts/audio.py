from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
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


def _concat_list_line(path: Path) -> str:
    return "file '" + str(path).replace("'", "'\\''") + "'"


def merge_wav_files(files: list[Path], target: Path, silence_ms: int = 40) -> Path:
    files = [path for path in files if path]
    if not files:
        raise AudioToolError("No audio files to merge.")
    for path in files:
        if not path.exists():
            raise AudioToolError(f"Audio file does not exist: {path}")

    target.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()
    with tempfile.TemporaryDirectory(prefix="xiaoyao-tts-merge-") as temp_name:
        temp_dir = Path(temp_name)
        concat_files = files
        normalized_silence_ms = max(0, min(5000, int(silence_ms or 0)))
        if normalized_silence_ms > 0 and len(files) > 1:
            silence_path = temp_dir / "silence.wav"
            silence_command = [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=16000:cl=mono",
                "-t",
                f"{normalized_silence_ms / 1000:.3f}",
                str(silence_path),
            ]
            result = subprocess.run(silence_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                message = result.stderr.strip() or "Failed to create merge silence with ffmpeg."
                raise AudioToolError(message)
            concat_files = []
            for index, path in enumerate(files):
                concat_files.append(path)
                if index < len(files) - 1:
                    concat_files.append(silence_path)

        list_path = temp_dir / "concat.txt"
        list_path.write_text("\n".join(_concat_list_line(path) for path in concat_files) + "\n", encoding="utf-8")
        temp_output = temp_dir / "final.wav"
        command = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-ac",
            "1",
            "-sample_fmt",
            "s16",
            str(temp_output),
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            message = result.stderr.strip() or "Failed to merge audio with ffmpeg."
            raise AudioToolError(message)
        temp_output.replace(target)
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
