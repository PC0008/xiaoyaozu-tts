from __future__ import annotations

from pathlib import Path

import soundfile as sf

from .config import DEFAULT_MODEL_ID
from .errors import BackendError
from .profiles import VoiceProfile


class VoxCPMBackend:
    def __init__(self, model_id: str = DEFAULT_MODEL_ID, device: str = "auto", denoise: bool = False) -> None:
        self.model_id = model_id
        self.device = device
        self.denoise = denoise
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from voxcpm import VoxCPM
        except Exception as exc:  # pragma: no cover - depends on optional runtime stack
            raise BackendError("voxcpm is required for speech generation.") from exc
        self._model = VoxCPM.from_pretrained(
            self.model_id,
            load_denoiser=self.denoise,
            device=self.device,
            optimize=self.device.startswith("cuda"),
        )
        return self._model

    def speak(
        self,
        *,
        profile: VoiceProfile,
        text: str,
        output_path: Path,
        cfg_value: float = 2.0,
        inference_timesteps: int = 10,
        normalize: bool = False,
    ) -> dict:
        text = text.strip()
        if not text:
            raise BackendError("Text cannot be empty.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        model = self._load_model()
        wav = model.generate(
            text=text,
            prompt_wav_path=str(profile.reference_wav_path),
            prompt_text=profile.transcript,
            reference_wav_path=str(profile.reference_wav_path),
            cfg_value=cfg_value,
            inference_timesteps=inference_timesteps,
            normalize=normalize,
            denoise=self.denoise,
        )
        sample_rate = model.tts_model.sample_rate
        sf.write(output_path, wav, sample_rate)
        duration_sec = len(wav) / float(sample_rate) if sample_rate else None
        return {
            "output": str(output_path.resolve()),
            "sample_rate": sample_rate,
            "duration_sec": duration_sec,
        }
