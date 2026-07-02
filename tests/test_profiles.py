from __future__ import annotations

import os
import io
import json
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from xiaoyao_tts.batch import load_batch_items
from xiaoyao_tts.cli import generate_speech, main
from xiaoyao_tts.config import profiles_dir
from xiaoyao_tts.engine import run_engine_server
from xiaoyao_tts.errors import AudioToolError
from xiaoyao_tts.history import list_generation_records, record_generation
from xiaoyao_tts.profiles import create_profile, slugify_profile_id, update_profile_transcript
from xiaoyao_tts.text_split import split_long_text


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


def test_long_text_split_prefers_natural_breaks():
    text = (
        "很多知识付费创业者，到今天还没有真正看懂 AI，他们以为 AI 就是写写文案，做做海报，剪剪视频，整理一下课件。"
        "如果你也是这样理解 AI 的，那么我必须提醒你一句：你可能把这轮机会，看得太浅了。"
        "AI 对知识付费创业者最大的改变，不是帮你省几个小时，而是它会重新定义一件事：你的经验，究竟还能不能卖钱？"
        "过去你卖课，是因为你有经验，别人没有。你会做流量，他不会；你会成交，他不会；你会写文案，他不会。"
        "但是今天问题来了，如果 AI 已经可以帮他写方案，拆流程，做诊断，改文案，生成 SOP，那么他还为什么必须听你一节一节讲？"
    )

    segments = split_long_text(text, "long")

    assert len(segments) >= 2
    assert all(len(segment.text) <= 200 for segment in segments)
    assert segments[0].text[-1] in "。！？!?；;，,、：:.．·"


def test_generate_speech_auto_segments_and_merges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    class FakeBackend:
        def speak(self, *, text: str, output_path: Path, **kwargs):
            calls.append(text)
            output_path.write_bytes(b"fake wav")
            return {
                "output": str(output_path),
                "sample_rate": 16000,
                "duration_sec": 1.0,
                "diagnostics": {"runtime": {"resolved_device": "cpu"}},
            }

    def fake_merge(files: list[Path], target: Path, silence_ms: int = 40):
        assert len(files) == len(calls)
        assert silence_ms == 40
        target.write_bytes(b"merged wav")
        return target

    monkeypatch.setattr("xiaoyao_tts.cli.merge_wav_files", fake_merge)
    monkeypatch.setattr("xiaoyao_tts.cli.audio_info", lambda path: {"sample_rate": 16000, "duration_sec": 3.0})

    text = (
        "很多知识付费创业者，到今天还没有真正看懂 AI，他们以为 AI 就是写写文案，做做海报，剪剪视频，整理一下课件。"
        "如果你也是这样理解 AI 的，那么我必须提醒你一句：你可能把这轮机会，看得太浅了。"
        "AI 对知识付费创业者最大的改变，不是帮你省几个小时，而是它会重新定义一件事：你的经验，究竟还能不能卖钱？"
        "过去你卖课，是因为你有经验，别人没有。你会做流量，他不会；你会成交，他不会；你会写文案，他不会。"
        "但是今天问题来了，如果 AI 已经可以帮他写方案，拆流程，做诊断，改文案，生成 SOP，那么他还为什么必须听你一节一节讲？"
    )
    result = generate_speech(
        backend=FakeBackend(),
        profile=SimpleNamespace(id="me"),
        text=text,
        output_path=tmp_path / "voice.wav",
        args=Namespace(
            cfg_value=2.0,
            inference_timesteps=10,
            normalize=False,
            speed=1.0,
            denoise=False,
            no_auto_segment=False,
            segment_threshold=180,
            segment_preset="long",
            segment_silence_ms=40,
        ),
    )

    assert len(calls) >= 2
    assert result["output"].endswith("voice.wav")
    assert result["segmented"] is True
    assert result["segments"] == len(calls)


def test_generate_speech_can_disable_auto_segment(tmp_path: Path):
    calls: list[str] = []

    class FakeBackend:
        def speak(self, *, text: str, output_path: Path, **kwargs):
            calls.append(text)
            output_path.write_bytes(b"fake wav")
            return {"output": str(output_path), "sample_rate": 16000, "duration_sec": 1.0}

    result = generate_speech(
        backend=FakeBackend(),
        profile=SimpleNamespace(id="me"),
        text="这是一段会超过阈值但主动关闭自动分段的文本。" * 20,
        output_path=tmp_path / "voice.wav",
        args=Namespace(
            cfg_value=2.0,
            inference_timesteps=10,
            normalize=False,
            speed=1.0,
            denoise=False,
            no_auto_segment=True,
            segment_threshold=180,
            segment_preset="long",
            segment_silence_ms=40,
        ),
    )

    assert len(calls) == 1
    assert "segmented" not in result


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
        speed=1.2,
    )
    assert [record.id for record in list_generation_records()] == [second.id, first.id]
    assert [record.id for record in list_generation_records(profile="me")] == [first.id]
    assert list_generation_records()[0].speed == 1.2
    assert list_generation_records()[1].speed == 1.0


def test_history_reads_old_records_without_speed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XIAOYAO_TTS_HOME", str(tmp_path / "home"))
    history_path = tmp_path / "home" / "history" / "generations.jsonl"
    history_path.parent.mkdir(parents=True)
    payload = {
        "id": "old",
        "created_at": "2026-01-01T00:00:00+00:00",
        "profile": "me",
        "text": "旧记录",
        "output": str(tmp_path / "old.wav"),
        "sample_rate": 48000,
        "duration_sec": 1.0,
        "device": "cpu",
        "model": "test",
        "cfg_value": 2.0,
        "inference_timesteps": 10,
        "source": "test",
    }
    history_path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")

    records = list_generation_records()

    assert len(records) == 1
    assert records[0].speed == 1.0


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


def test_cli_transcribe_outputs_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    source = tmp_path / "ref.wav"
    source.write_bytes(b"fake audio")

    def fake_transcribe(self, audio_path: Path):
        assert audio_path == source.resolve()
        return "自动识别出来的参考文稿"

    monkeypatch.setattr("xiaoyao_tts.cli.SenseVoiceASR.transcribe", fake_transcribe)

    exit_code = main(["transcribe", "--audio", str(source), "--json"])

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["text"] == "自动识别出来的参考文稿"


def test_engine_server_ping_shutdown():
    stdin = io.StringIO('{"id":"one","method":"ping"}\n{"id":"two","method":"shutdown"}\n')
    stdout = io.StringIO()

    exit_code = run_engine_server(stdin=stdin, stdout=stdout)

    lines = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert exit_code == 0
    assert lines[0]["ok"] is True
    assert lines[0]["id"] == "one"
    assert lines[0]["result"]["device"] == "auto"
    assert lines[1]["ok"] is True
    assert lines[1]["shutdown"] is True
