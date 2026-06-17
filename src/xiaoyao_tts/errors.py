from __future__ import annotations


class XiaoyaoTTSError(Exception):
    code = "xiaoyao_tts_error"


class AudioToolError(XiaoyaoTTSError):
    code = "audio_tool_error"


class ProfileError(XiaoyaoTTSError):
    code = "profile_error"


class BackendError(XiaoyaoTTSError):
    code = "backend_error"
