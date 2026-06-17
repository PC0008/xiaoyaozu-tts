from __future__ import annotations

from pathlib import Path

from .errors import BackendError


class SenseVoiceASR:
    def __init__(self, model_id: str = "iic/SenseVoiceSmall", device: str = "cpu") -> None:
        self.model_id = model_id
        self.device = device
        self._model = None

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from funasr import AutoModel
        except Exception as exc:  # pragma: no cover - depends on optional runtime stack
            raise BackendError("funasr is required for automatic transcription.") from exc
        self._model = AutoModel(
            model=self.model_id,
            disable_update=True,
            log_level="ERROR",
            device=self.device,
        )
        return self._model

    def transcribe(self, audio_path: Path) -> str:
        if not audio_path.exists():
            raise BackendError(f"Audio file does not exist: {audio_path}")
        result = self._load().generate(input=str(audio_path), language="auto", use_itn=True)
        if not result:
            raise BackendError("ASR returned an empty result.")
        text = result[0].get("text", "")
        return text.split("|>")[-1].strip()
