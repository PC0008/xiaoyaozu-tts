from __future__ import annotations

import contextlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import TextIO

from .backend import VoxCPMBackend
from .config import DEFAULT_MODEL_ID
from .history import record_generation
from .profiles import load_profile


def _json_line(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


class EngineServer:
    def __init__(
        self,
        *,
        model_id: str = DEFAULT_MODEL_ID,
        device: str = "auto",
        denoise: bool = False,
    ) -> None:
        self.model_id = model_id
        self.device = device
        self.backend = VoxCPMBackend(model_id=model_id, device=device, denoise=denoise)

    def handle(self, request: dict) -> dict:
        request_id = request.get("id")
        method = request.get("method")
        try:
            if method == "ping":
                return {"id": request_id, "ok": True, "result": {"device": self.device, "model": self.model_id}}
            if method == "shutdown":
                return {"id": request_id, "ok": True, "result": {"message": "bye"}, "shutdown": True}
            if method == "speak":
                return {"id": request_id, "ok": True, "result": self._speak(request)}
            raise ValueError(f"Unsupported engine method: {method}")
        except Exception as exc:
            code = getattr(exc, "code", "error")
            return {"id": request_id, "ok": False, "error": code, "message": str(exc)}

    def _speak(self, request: dict) -> dict:
        params = request.get("params") or {}
        profile_id = str(params.get("profile") or "").strip()
        text = str(params.get("text") or "").strip()
        output = str(params.get("output") or "").strip()
        if not profile_id:
            raise ValueError("Missing profile.")
        if not text:
            raise ValueError("Missing text.")
        if not output:
            raise ValueError("Missing output.")

        profile = load_profile(profile_id)
        cfg_value = float(params.get("cfg_value", 2.0))
        inference_timesteps = int(params.get("inference_timesteps", 10))
        normalize = bool(params.get("normalize", False))
        speed = float(params.get("speed", 1.0))
        source = str(params.get("source") or "engine")
        batch_id = params.get("batch_id")
        item_id = params.get("item_id")

        with contextlib.redirect_stdout(sys.stderr):
            result = self.backend.speak(
                profile=profile,
                text=text,
                output_path=Path(output).expanduser().resolve(),
                cfg_value=cfg_value,
                inference_timesteps=inference_timesteps,
                normalize=normalize,
                speed=speed,
            )

        record = record_generation(
            profile=profile.id,
            text=text,
            output=result["output"],
            sample_rate=result.get("sample_rate"),
            duration_sec=result.get("duration_sec"),
            device=self.device,
            model=self.model_id,
            cfg_value=cfg_value,
            inference_timesteps=inference_timesteps,
            source=source,
            speed=speed,
            batch_id=str(batch_id) if batch_id else None,
            item_id=str(item_id) if item_id else None,
        )
        return {"profile": profile.id, **result, "history": asdict(record), "message": f"Saved: {result['output']}"}


def run_engine_server(
    *,
    model_id: str = DEFAULT_MODEL_ID,
    device: str = "auto",
    denoise: bool = False,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    server = EngineServer(model_id=model_id, device=device, denoise=denoise)
    input_stream = stdin or sys.stdin
    output_stream = stdout or sys.stdout

    for raw_line in input_stream:
        line = raw_line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = server.handle(request)
        except Exception as exc:
            code = getattr(exc, "code", "error")
            response = {"id": None, "ok": False, "error": code, "message": str(exc)}
        output_stream.write(_json_line(response) + "\n")
        output_stream.flush()
        if response.get("shutdown"):
            break
    return 0
