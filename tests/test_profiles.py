from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from xiaoyao_tts.batch import load_batch_items
from xiaoyao_tts.config import profiles_dir
from xiaoyao_tts.errors import AudioToolError
from xiaoyao_tts.history import list_generation_records, record_generation
from xiaoyao_tts.profiles import create_profile, slugify_profile_id, update_profile_transcript


def test_slugify_profile_id_keeps_chinese_and_ascii():
    assert slugify_profile_id("我的 Voice 01") == "我的-voice-01"


def test_cli_lists_empty_profiles(tmp_path: Path):
    env = os.environ.copy()
    env["XIAOYAO_TTS_HOME"] = str(tmp_path / "home")
    result = subprocess.run(
        [sys.executable, "-m", "xiaoyao_tts.cli", "profile", "list", "--json"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    assert '"ok": true' in result.stdout
    assert '"profiles": []' in result.stdout


def test_batch_loader_supports_txt_and_jsonl(tmp_path: Path):
    txt = tmp_path / "scripts.txt"
    txt.write_text("# comment\n第一条\n\n第二条\n", encoding="utf-8")
    txt_items = load_batch_items(txt)
    assert [item.id for item in txt_items] == ["line-002", "line-004"]
    assert [item.text for item in txt_items] == ["第一条", "第二条"]

    jsonl = tmp_path / "scripts.jsonl"
    jsonl.write_text('{"id": "scene 01", "text": "开场"}\n{"text": "结尾"}\n', encoding="utf-8")
    jsonl_items = load_batch_items(jsonl)
    assert jsonl_items[0].id == "scene-01"
    assert jsonl_items[0].text == "开场"
    assert jsonl_items[1].id == "item-002"


def test_history_records_are_listed_newest_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XIAOYAO_TTS_HOME", str(tmp_path / "home"))
    first = record_generation(
        profile="me",
        text="第一条",
        output=tmp_path / "one.wav",
        sample_rate=48000,
        duration_sec=1.0,
        device="cpu",
        model="test-model",
        cfg_value=2.0,
        inference_timesteps=4,
        source="test",
    )
    second = record_generation(
        profile="friend",
        text="第二条",
        output=tmp_path / "two.wav",
        sample_rate=48000,
        duration_sec=2.0,
        device="cpu",
        model="test-model",
        cfg_value=2.0,
        inference_timesteps=4,
        source="test",
    )
    assert [record.id for record in list_generation_records()] == [second.id, first.id]
    assert [record.id for record in list_generation_records(profile="me")] == [first.id]


def test_update_profile_transcript(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg is required for profile audio conversion")
    monkeypatch.setenv("XIAOYAO_TTS_HOME", str(tmp_path / "home"))
    source = tmp_path / "ref.wav"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.2",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(source),
        ],
        check=True,
    )
    profile = create_profile(name="me", audio_path=source, transcript="旧文稿")
    updated = update_profile_transcript(profile.id, "新文稿")
    assert updated.transcript == "新文稿"
    assert updated.updated_at != profile.updated_at


def test_create_profile_cleans_partial_directory_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XIAOYAO_TTS_HOME", str(tmp_path / "home"))
    source = tmp_path / "ref.wav"
    source.write_bytes(b"not real audio")

    def fail_convert(*args, **kwargs):
        raise AudioToolError("simulated conversion failure")

    monkeypatch.setattr("xiaoyao_tts.profiles.convert_to_reference_wav", fail_convert)

    with pytest.raises(AudioToolError):
        create_profile(name="智多星1", audio_path=source, transcript="测试文稿")

    assert not (profiles_dir() / "智多星1").exists()
