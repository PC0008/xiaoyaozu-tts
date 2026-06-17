from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from xiaoyao_tts.profiles import slugify_profile_id


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
