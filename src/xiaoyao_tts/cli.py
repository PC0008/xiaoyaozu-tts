from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .asr import SenseVoiceASR
from .audio import find_ffmpeg
from .batch import load_batch_items
from .backend import VoxCPMBackend
from .config import DEFAULT_MODEL_ID, app_home, ensure_app_dirs
from .engine import run_engine_server
from .errors import InputError, XiaoyaoTTSError
from .history import list_generation_records, new_batch_id, record_generation
from .profiles import create_profile, delete_profile, list_profiles, load_profile, update_profile_transcript
from .setup_models import cache_status, download_models, status_as_dicts


def emit_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2))


@contextlib.contextmanager
def noisy_runtime(as_json: bool):
    if as_json:
        with contextlib.redirect_stdout(sys.stderr):
            yield
    else:
        yield


def ok(payload: dict | None = None, *, as_json: bool = False) -> None:
    if as_json:
        emit_json({"ok": True, **(payload or {})})
    elif payload and payload.get("message"):
        print(payload["message"])


def fail(exc: Exception, *, as_json: bool = False) -> int:
    code = getattr(exc, "code", "error")
    if as_json:
        emit_json({"ok": False, "error": code, "message": str(exc)})
    else:
        print(f"Error [{code}]: {exc}", file=sys.stderr)
    return 1


def read_text_arg(text: str | None, text_file: str | None) -> str:
    if text and text_file:
        raise InputError("Use either --text or --text-file, not both.")
    if text_file:
        return Path(text_file).read_text(encoding="utf-8").strip()
    if text:
        return text.strip()
    raise InputError("Missing text. Use --text or --text-file.")


def read_transcript_arg(value: str | None, transcript_file: str | None) -> str | None:
    if value and transcript_file:
        raise InputError("Use either --transcript or --transcript-file, not both.")
    if transcript_file:
        return Path(transcript_file).read_text(encoding="utf-8").strip()
    return value.strip() if value else None


def command_doctor(args: argparse.Namespace) -> int:
    ensure_app_dirs()
    ffmpeg_path = find_ffmpeg()
    voxcpm_available = importlib.util.find_spec("voxcpm") is not None
    funasr_available = importlib.util.find_spec("funasr") is not None
    payload = {
        "version": __version__,
        "python": platform.python_version(),
        "home": str(app_home()),
        "ffmpeg": ffmpeg_path,
        "voxcpm_available": voxcpm_available,
        "funasr_available": funasr_available,
        "models": status_as_dicts(),
        "profiles": len(list_profiles()),
    }
    ok(payload, as_json=args.json)
    if not args.json:
        print(f"逍遥族TTS {payload['version']}")
        print(f"Python: {payload['python']}")
        print(f"Home: {payload['home']}")
        print(f"ffmpeg: {payload['ffmpeg']}")
        print(f"VoxCPM: {'available' if payload['voxcpm_available'] else 'missing'}")
        print(f"FunASR: {'available' if payload['funasr_available'] else 'missing'}")
        for status in cache_status():
            state = "cached" if status.cached else "missing"
            print(f"Model {status.name}: {state} ({status.size_human})")
        print(f"Profiles: {payload['profiles']}")
    return 0


def command_profile_create(args: argparse.Namespace) -> int:
    audio_path = Path(args.audio).expanduser().resolve()
    transcript = read_transcript_arg(args.transcript, args.transcript_file)
    if transcript is None:
        print("Transcribing reference audio...", file=sys.stderr)
        with noisy_runtime(args.json):
            transcript = SenseVoiceASR(device=args.asr_device).transcribe(audio_path)
    profile = create_profile(
        name=args.name,
        profile_id=args.id,
        audio_path=audio_path,
        transcript=transcript,
        consent=args.consent,
        overwrite=args.overwrite,
    )
    payload = {"profile": asdict(profile), "message": f"Created voice profile: {profile.id}"}
    ok(payload, as_json=args.json)
    if not args.json:
        print(payload["message"])
        print(f"Transcript: {profile.transcript_path}")
        print(f"Reference WAV: {profile.reference_wav_path}")
    return 0


def command_profile_list(args: argparse.Namespace) -> int:
    profiles = [asdict(profile) for profile in list_profiles()]
    if args.json:
        ok({"profiles": profiles}, as_json=True)
    else:
        if not profiles:
            print("No voice profiles yet.")
            return 0
        for profile in profiles:
            duration = profile.get("duration_sec")
            duration_text = f"{duration:.1f}s" if duration else "unknown"
            print(f"{profile['id']}\t{profile['name']}\t{duration_text}")
    return 0


def command_profile_inspect(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    payload = asdict(profile)
    payload["transcript"] = profile.transcript
    if args.json:
        ok({"profile": payload}, as_json=True)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_profile_delete(args: argparse.Namespace) -> int:
    delete_profile(args.profile)
    ok({"message": f"Deleted voice profile: {args.profile}"}, as_json=args.json)
    if not args.json:
        print(f"Deleted voice profile: {args.profile}")
    return 0


def command_profile_update_transcript(args: argparse.Namespace) -> int:
    transcript = read_transcript_arg(args.transcript, args.transcript_file)
    if transcript is None:
        raise InputError("Missing transcript. Use --transcript or --transcript-file.")
    profile = update_profile_transcript(args.profile, transcript)
    payload = {
        "profile": asdict(profile),
        "transcript": profile.transcript,
        "message": f"Updated transcript for voice profile: {profile.id}",
    }
    ok(payload, as_json=args.json)
    if not args.json:
        print(payload["message"])
    return 0


def command_transcribe(args: argparse.Namespace) -> int:
    audio_path = Path(args.audio).expanduser().resolve()
    with noisy_runtime(args.json):
        text = SenseVoiceASR(device=args.device).transcribe(audio_path)
    payload = {"text": text, "message": "Transcribed reference audio"}
    ok(payload, as_json=args.json)
    if not args.json:
        print(text)
    return 0


def command_speak(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    text = read_text_arg(args.text, args.text_file)
    backend = VoxCPMBackend(model_id=args.model, device=args.device, denoise=args.denoise)
    with noisy_runtime(args.json):
        result = backend.speak(
            profile=profile,
            text=text,
            output_path=Path(args.out).expanduser().resolve(),
            cfg_value=args.cfg_value,
            inference_timesteps=args.inference_timesteps,
            normalize=args.normalize,
        )
    record = record_generation(
        profile=profile.id,
        text=text,
        output=result["output"],
        sample_rate=result.get("sample_rate"),
        duration_sec=result.get("duration_sec"),
        device=args.device,
        model=args.model,
        cfg_value=args.cfg_value,
        inference_timesteps=args.inference_timesteps,
        source="speak",
    )
    payload = {"profile": profile.id, **result, "message": f"Saved: {result['output']}"}
    payload["history"] = asdict(record)
    ok(payload, as_json=args.json)
    if not args.json:
        print(payload["message"])
    return 0


def command_batch(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    input_path = Path(args.input).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    items = load_batch_items(input_path, args.format)
    backend = VoxCPMBackend(model_id=args.model, device=args.device, denoise=args.denoise)
    batch_id = new_batch_id()
    results = []
    for index, item in enumerate(items, start=1):
        output_path = out_dir / f"{index:03d}-{item.id}.wav"
        with noisy_runtime(args.json):
            result = backend.speak(
                profile=profile,
                text=item.text,
                output_path=output_path,
                cfg_value=args.cfg_value,
                inference_timesteps=args.inference_timesteps,
                normalize=args.normalize,
            )
        record = record_generation(
            profile=profile.id,
            text=item.text,
            output=result["output"],
            sample_rate=result.get("sample_rate"),
            duration_sec=result.get("duration_sec"),
            device=args.device,
            model=args.model,
            cfg_value=args.cfg_value,
            inference_timesteps=args.inference_timesteps,
            source="batch",
            batch_id=batch_id,
            item_id=item.id,
        )
        item_payload = {"id": item.id, **result, "history": asdict(record)}
        results.append(item_payload)
        if not args.json:
            print(f"[{index}/{len(items)}] Saved: {result['output']}")
    payload = {
        "batch_id": batch_id,
        "profile": profile.id,
        "count": len(results),
        "results": results,
        "message": f"Generated {len(results)} files in {out_dir}",
    }
    ok(payload, as_json=args.json)
    if not args.json:
        print(payload["message"])
    return 0


def command_history_list(args: argparse.Namespace) -> int:
    records = [asdict(record) for record in list_generation_records(limit=args.limit, profile=args.profile)]
    if args.json:
        ok({"history": records}, as_json=True)
    else:
        if not records:
            print("No generation history yet.")
            return 0
        for record in records:
            duration = record.get("duration_sec")
            duration_text = f"{duration:.1f}s" if duration else "unknown"
            print(f"{record['created_at']}\t{record['profile']}\t{duration_text}\t{record['output']}")
    return 0


def command_setup_download_models(args: argparse.Namespace) -> int:
    with noisy_runtime(args.json):
        statuses = download_models(include_asr=not args.no_asr, include_denoiser=args.include_denoiser)
    payload = {
        "models": [asdict(status) for status in statuses],
        "message": "Downloaded runtime models.",
    }
    ok(payload, as_json=args.json)
    if not args.json:
        print(payload["message"])
        for status in statuses:
            print(f"{status.name}: {status.size_human} at {status.path}")
    return 0


def command_setup_status(args: argparse.Namespace) -> int:
    statuses = cache_status()
    payload = {"models": [asdict(status) for status in statuses]}
    ok(payload, as_json=args.json)
    if not args.json:
        for status in statuses:
            state = "cached" if status.cached else "missing"
            print(f"{status.name}\t{state}\t{status.size_human}\t{status.path or '-'}")
    return 0


def command_serve(args: argparse.Namespace) -> int:
    return run_engine_server(model_id=args.model, device=args.device, denoise=args.denoise)


def add_generation_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--cfg-value", type=float, default=2.0)
    parser.add_argument("--inference-timesteps", type=int, default=10)
    parser.add_argument("--normalize", action="store_true")
    parser.add_argument("--denoise", action="store_true", help="Enable reference audio denoising. WAV profiles are recommended.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xiaoyao-tts", description="逍遥族TTS local voice profile toolkit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local runtime requirements")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=command_doctor)

    setup = subparsers.add_parser("setup", help="Prepare runtime models and inspect cache status")
    setup_sub = setup.add_subparsers(dest="setup_command", required=True)

    download = setup_sub.add_parser("download-models", help="Download VoxCPM2 and ASR models before first generation")
    download.add_argument("--no-asr", action="store_true", help="Only download VoxCPM2; skip SenseVoice ASR")
    download.add_argument("--include-denoiser", action="store_true", help="Also download the optional ZipEnhancer denoiser")
    download.add_argument("--json", action="store_true")
    download.set_defaults(func=command_setup_download_models)

    setup_status = setup_sub.add_parser("status", help="Show local model cache status")
    setup_status.add_argument("--json", action="store_true")
    setup_status.set_defaults(func=command_setup_status)

    profile = subparsers.add_parser("profile", help="Manage voice profiles")
    profile_sub = profile.add_subparsers(dest="profile_command", required=True)

    create = profile_sub.add_parser("create", help="Create a reusable voice profile")
    create.add_argument("--name", required=True, help="Display name for the voice profile")
    create.add_argument("--id", help="Stable profile id. Defaults to a slug from --name")
    create.add_argument("--audio", required=True, help="Reference recording path, such as .m4a/.mp3/.wav")
    create.add_argument("--transcript", help="Transcript of the reference recording")
    create.add_argument("--transcript-file", help="Text file containing the transcript")
    create.add_argument("--asr-device", default="cpu", help="ASR device, default: cpu")
    create.add_argument("--consent", default="self", help="Consent note, default: self")
    create.add_argument("--overwrite", action="store_true", help="Replace an existing profile with the same id")
    create.add_argument("--json", action="store_true")
    create.set_defaults(func=command_profile_create)

    list_cmd = profile_sub.add_parser("list", help="List voice profiles")
    list_cmd.add_argument("--json", action="store_true")
    list_cmd.set_defaults(func=command_profile_list)

    inspect = profile_sub.add_parser("inspect", help="Inspect one voice profile")
    inspect.add_argument("profile")
    inspect.add_argument("--json", action="store_true")
    inspect.set_defaults(func=command_profile_inspect)

    delete = profile_sub.add_parser("delete", help="Delete one voice profile")
    delete.add_argument("profile")
    delete.add_argument("--json", action="store_true")
    delete.set_defaults(func=command_profile_delete)

    update_transcript = profile_sub.add_parser("update-transcript", help="Update the cached transcript for one voice profile")
    update_transcript.add_argument("profile")
    update_transcript.add_argument("--transcript")
    update_transcript.add_argument("--transcript-file")
    update_transcript.add_argument("--json", action="store_true")
    update_transcript.set_defaults(func=command_profile_update_transcript)

    transcribe = subparsers.add_parser("transcribe", help="Transcribe reference audio without creating a voice profile")
    transcribe.add_argument("--audio", required=True, help="Reference recording path, such as .m4a/.mp3/.wav")
    transcribe.add_argument("--device", default="cpu", help="ASR device, default: cpu")
    transcribe.add_argument("--json", action="store_true")
    transcribe.set_defaults(func=command_transcribe)

    serve = subparsers.add_parser("serve", help="Run a persistent JSONL speech generation engine")
    serve.add_argument("--model", default=DEFAULT_MODEL_ID)
    serve.add_argument("--device", default="auto")
    serve.add_argument("--denoise", action="store_true", help="Enable reference audio denoising for the persistent engine")
    serve.set_defaults(func=command_serve)

    speak = subparsers.add_parser("speak", help="Generate speech with one voice profile")
    speak.add_argument("--profile", required=True)
    speak.add_argument("--text")
    speak.add_argument("--text-file")
    speak.add_argument("--out", required=True)
    add_generation_options(speak)
    speak.add_argument("--json", action="store_true")
    speak.set_defaults(func=command_speak)

    batch = subparsers.add_parser("batch", help="Generate multiple speech files from a txt or JSONL input")
    batch.add_argument("--profile", required=True)
    batch.add_argument("--input", required=True)
    batch.add_argument("--out-dir", required=True)
    batch.add_argument("--format", choices=["auto", "txt", "jsonl"], default="auto")
    add_generation_options(batch)
    batch.add_argument("--json", action="store_true")
    batch.set_defaults(func=command_batch)

    history = subparsers.add_parser("history", help="Inspect generation history")
    history_sub = history.add_subparsers(dest="history_command", required=True)
    history_list = history_sub.add_parser("list", help="List recent generation records")
    history_list.add_argument("--limit", type=int, default=20)
    history_list.add_argument("--profile")
    history_list.add_argument("--json", action="store_true")
    history_list.set_defaults(func=command_history_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        return fail(exc, as_json=getattr(args, "json", False))


if __name__ == "__main__":
    raise SystemExit(main())
