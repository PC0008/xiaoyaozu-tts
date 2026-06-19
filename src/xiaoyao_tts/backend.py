from __future__ import annotations

import platform
import sys
import time
from importlib import metadata
from pathlib import Path

import soundfile as sf

from .audio import audio_info, change_audio_speed
from .config import DEFAULT_MODEL_ID
from .errors import BackendError
from .profiles import VoiceProfile


class VoxCPMBackend:
    def __init__(self, model_id: str = DEFAULT_MODEL_ID, device: str = "auto", denoise: bool = False) -> None:
        self.model_id = model_id
        self.device = device
        self.denoise = denoise
        self._model = None
        self.resolved_device = device
        self.optimize = False
        self._runtime = self._collect_runtime_info()
        self._last_model_load_seconds = 0.0

    def _collect_runtime_info(self) -> dict:
        info = {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "requested_device": self.device,
            "resolved_device": self.resolved_device,
            "optimize": self.optimize,
            "model_id": self.model_id,
            "denoise": self.denoise,
        }
        try:
            info["voxcpm_version"] = metadata.version("voxcpm")
        except Exception:
            info["voxcpm_version"] = "unknown"

        try:
            import voxcpm

            info["voxcpm_file"] = getattr(voxcpm, "__file__", "")
        except Exception as exc:
            info["voxcpm_file"] = f"unavailable: {exc}"

        try:
            import torch

            info.update(
                {
                    "torch_version": torch.__version__,
                    "torch_file": getattr(torch, "__file__", ""),
                    "torch_cuda_available": bool(torch.cuda.is_available()),
                    "torch_cuda_version": getattr(torch.version, "cuda", None),
                    "torch_cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
                    "torch_cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                    "torch_cudnn_version": torch.backends.cudnn.version() if torch.cuda.is_available() else None,
                    "torch_mps_available": bool(
                        hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
                    ),
                }
            )
        except Exception as exc:
            info["torch_error"] = str(exc)
        return info

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from voxcpm import VoxCPM
            from voxcpm.model.utils import resolve_runtime_device
        except Exception as exc:  # pragma: no cover - depends on optional runtime stack
            raise BackendError("voxcpm is required for speech generation.") from exc
        self.resolved_device = resolve_runtime_device(self.device, "cuda")
        self.optimize = self.resolved_device.startswith("cuda")
        self._runtime = self._collect_runtime_info()
        load_started = time.perf_counter()
        self._model = VoxCPM.from_pretrained(
            self.model_id,
            load_denoiser=self.denoise,
            device=self.resolved_device,
            optimize=self.optimize,
        )
        self._last_model_load_seconds = time.perf_counter() - load_started
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
        speed: float = 1.0,
    ) -> dict:
        text = text.strip()
        if not text:
            raise BackendError("Text cannot be empty.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        total_started = time.perf_counter()
        was_loaded = self._model is not None
        model = self._load_model()
        model_load_seconds = 0.0 if was_loaded else self._last_model_load_seconds
        generate_started = time.perf_counter()
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
        generate_seconds = time.perf_counter() - generate_started
        sample_rate = model.tts_model.sample_rate
        postprocess_started = time.perf_counter()
        if abs(speed - 1.0) < 0.001:
            sf.write(output_path, wav, sample_rate)
            duration_sec = len(wav) / float(sample_rate) if sample_rate else None
        else:
            temp_path = output_path.with_name(f"{output_path.stem}.raw{output_path.suffix}")
            sf.write(temp_path, wav, sample_rate)
            try:
                change_audio_speed(temp_path, output_path, speed)
                duration_sec = audio_info(output_path).get("duration_sec")
            finally:
                temp_path.unlink(missing_ok=True)
        postprocess_seconds = time.perf_counter() - postprocess_started
        total_seconds = time.perf_counter() - total_started
        return {
            "output": str(output_path.resolve()),
            "sample_rate": sample_rate,
            "duration_sec": duration_sec,
            "speed": speed,
            "diagnostics": {
                "runtime": {
                    **self._runtime,
                    "requested_device": self.device,
                    "resolved_device": self.resolved_device,
                    "optimize": self.optimize,
                },
                "params": {
                    "text_chars": len(text),
                    "cfg_value": cfg_value,
                    "inference_timesteps": inference_timesteps,
                    "normalize": normalize,
                    "speed": speed,
                    "denoise": self.denoise,
                    "profile": profile.id,
                },
                "timing": {
                    "model_was_loaded": was_loaded,
                    "model_load_seconds": round(model_load_seconds, 3),
                    "generate_seconds": round(generate_seconds, 3),
                    "postprocess_seconds": round(postprocess_seconds, 3),
                    "total_seconds": round(total_seconds, 3),
                    "audio_duration_seconds": round(duration_sec, 3) if duration_sec is not None else None,
                    "rtf": round(total_seconds / duration_sec, 3) if duration_sec else None,
                },
            },
        }
