from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .audio import audio_info, convert_to_reference_wav
from .config import DEFAULT_SAMPLE_RATE, ensure_app_dirs, profiles_dir
from .errors import ProfileError


@dataclass
class VoiceProfile:
    id: str
    name: str
    created_at: str
    updated_at: str
    source_audio: str
    reference_wav: str
    transcript_file: str
    duration_sec: float | None
    sample_rate: int
    consent: str

    @property
    def root(self) -> Path:
        return profiles_dir() / self.id

    @property
    def reference_wav_path(self) -> Path:
        return self.root / self.reference_wav

    @property
    def transcript_path(self) -> Path:
        return self.root / self.transcript_file

    @property
    def transcript(self) -> str:
        return self.transcript_path.read_text(encoding="utf-8").strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify_profile_id(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff_-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-_")
    if not value:
        raise ProfileError("Profile id cannot be empty.")
    return value


def profile_path(profile_id: str) -> Path:
    return profiles_dir() / slugify_profile_id(profile_id)


def metadata_path(profile_id: str) -> Path:
    return profile_path(profile_id) / "profile.json"


def load_profile(profile_id: str) -> VoiceProfile:
    path = metadata_path(profile_id)
    if not path.exists():
        raise ProfileError(f"Voice profile does not exist: {profile_id}")
    return VoiceProfile(**json.loads(path.read_text(encoding="utf-8")))


def save_profile(profile: VoiceProfile) -> VoiceProfile:
    path = metadata_path(profile.id)
    if not path.exists():
        raise ProfileError(f"Voice profile does not exist: {profile.id}")
    profile.updated_at = utc_now()
    path.write_text(json.dumps(asdict(profile), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return profile


def list_profiles() -> list[VoiceProfile]:
    ensure_app_dirs()
    items: list[VoiceProfile] = []
    for path in sorted(profiles_dir().iterdir()):
        meta = path / "profile.json"
        if meta.exists():
            items.append(VoiceProfile(**json.loads(meta.read_text(encoding="utf-8"))))
    return items


def create_profile(
    *,
    name: str,
    audio_path: Path,
    transcript: str,
    profile_id: str | None = None,
    consent: str = "self",
    overwrite: bool = False,
) -> VoiceProfile:
    ensure_app_dirs()
    final_id = slugify_profile_id(profile_id or name)
    root = profiles_dir() / final_id
    if root.exists() and not overwrite:
        raise ProfileError(f"Voice profile already exists: {final_id}. Use --overwrite to replace it.")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    suffix = audio_path.suffix.lower() or ".audio"
    source_name = f"source{suffix}"
    source_target = root / source_name
    shutil.copy2(audio_path, source_target)
    reference_target = root / "reference.wav"
    convert_to_reference_wav(source_target, reference_target, sample_rate=DEFAULT_SAMPLE_RATE)

    transcript = transcript.strip()
    if not transcript:
        raise ProfileError("Transcript cannot be empty.")
    transcript_file = root / "transcript.txt"
    transcript_file.write_text(transcript + "\n", encoding="utf-8")

    info = audio_info(reference_target)
    now = utc_now()
    profile = VoiceProfile(
        id=final_id,
        name=name,
        created_at=now,
        updated_at=now,
        source_audio=source_name,
        reference_wav="reference.wav",
        transcript_file="transcript.txt",
        duration_sec=info.get("duration_sec"),
        sample_rate=DEFAULT_SAMPLE_RATE,
        consent=consent,
    )
    (root / "profile.json").write_text(json.dumps(asdict(profile), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return profile


def update_profile_transcript(profile_id: str, transcript: str) -> VoiceProfile:
    transcript = transcript.strip()
    if not transcript:
        raise ProfileError("Transcript cannot be empty.")
    profile = load_profile(profile_id)
    profile.transcript_path.write_text(transcript + "\n", encoding="utf-8")
    return save_profile(profile)


def delete_profile(profile_id: str) -> None:
    root = profile_path(profile_id)
    if not root.exists():
        raise ProfileError(f"Voice profile does not exist: {profile_id}")
    shutil.rmtree(root)
