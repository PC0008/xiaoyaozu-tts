from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .asr import SenseVoiceASR
from .audio import find_ffmpeg
from .backend import VoxCPMBackend
from .config import DEFAULT_MODEL_ID, app_home, ensure_app_dirs
from .errors import XiaoyaoTTSError
from .profiles import create_profile, delete_profile, list_profiles, load_profile


def emit_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


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
        raise XiaoyaoTTSError("Use either --text or --text-file, not both.")
    if text_file:
        return Path(text_file).read_text(encoding="utf-8").strip()
    if text:
        return text.strip()
    raise XiaoyaoTTSError("Missing text. Use --text or --text-file.")


def read_transcript_arg(value: str | None, transcript_file: str | None) -> str | None:
    if value and transcript_file:
        raise XiaoyaoTTSError("Use either --transcript or --transcript-file, not both.")
    if transcript_file:
        return Path(transcript_file).read_text(encoding="utf-8").strip()
    return value.strip() if value else None


def command_doctor(args: argparse.Namespace) -> int:
    ensure_app_dirs()
    ffmpeg_path = find_ffmpeg()
    payload = {
        "version": __version__,
        "home": str(app_home()),
        "ffmpeg": ffmpeg_path,
        "profiles": len(list_profiles()),
    }
    ok(payload, as_json=args.json)
    if not args.json:
        print(f"逍遥族TTS {payload['version']}")
        print(f"Home: {payload['home']}")
        print(f"ffmpeg: {payload['ffmpeg']}")
        print(f"Profiles: {payload['profiles']}")
    return 0


def command_profile_create(args: argparse.Namespace) -> int:
    audio_path = Path(args.audio).expanduser().resolve()
    transcript = read_transcript_arg(args.transcript, args.transcript_file)
    if transcript is None:
        print("Transcribing reference audio...", file=sys.stderr)
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


def command_speak(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    text = read_text_arg(args.text, args.text_file)
    backend = VoxCPMBackend(model_id=args.model, device=args.device, denoise=args.denoise)
    result = backend.speak(
        profile=profile,
        text=text,
        output_path=Path(args.out).expanduser().resolve(),
        cfg_value=args.cfg_value,
        inference_timesteps=args.inference_timesteps,
        normalize=args.normalize,
    )
    payload = {"profile": profile.id, **result, "message": f"Saved: {result['output']}"}
    ok(payload, as_json=args.json)
    if not args.json:
        print(payload["message"])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xiaoyao-tts", description="逍遥族TTS local voice profile toolkit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local runtime requirements")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=command_doctor)

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

    speak = subparsers.add_parser("speak", help="Generate speech with one voice profile")
    speak.add_argument("--profile", required=True)
    speak.add_argument("--text")
    speak.add_argument("--text-file")
    speak.add_argument("--out", required=True)
    speak.add_argument("--model", default=DEFAULT_MODEL_ID)
    speak.add_argument("--device", default="auto")
    speak.add_argument("--cfg-value", type=float, default=2.0)
    speak.add_argument("--inference-timesteps", type=int, default=10)
    speak.add_argument("--normalize", action="store_true")
    speak.add_argument("--denoise", action="store_true", help="Enable reference audio denoising. WAV profiles are recommended.")
    speak.add_argument("--json", action="store_true")
    speak.set_defaults(func=command_speak)

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
