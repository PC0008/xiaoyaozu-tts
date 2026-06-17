# Agent Usage

逍遥族TTS 的 CLI 可以给 agents 或自动化工作流调用。

## Rules For Reliable Calls

- Use `--json` for machine-readable output.
- Read final results from `stdout`.
- Treat progress logs and model loading logs on `stderr` as non-fatal unless exit code is non-zero.
- Use `--text-file` for long scripts.
- Use stable profile ids instead of display names when automating.

## Discover Voices

```bash
xiaoyao-tts profile list --json
```

Example output:

```json
{
  "ok": true,
  "profiles": [
    {
      "id": "me",
      "name": "me",
      "reference_wav": "reference.wav"
    }
  ]
}
```

## Generate One File

```bash
xiaoyao-tts speak \
  --profile me \
  --text-file script.txt \
  --out outputs/agent.wav \
  --device mps \
  --json
```

Successful output:

```json
{
  "ok": true,
  "profile": "me",
  "output": "/abs/path/outputs/agent.wav",
  "sample_rate": 48000,
  "duration_sec": 3.2
}
```

Failure output:

```json
{
  "ok": false,
  "error": "profile_error",
  "message": "Voice profile does not exist: unknown"
}
```

## Batch Files

```bash
xiaoyao-tts batch \
  --profile me \
  --input scripts.jsonl \
  --out-dir outputs/batch \
  --json
```

Each generated file is also written to generation history.

## Current Error Codes

- `invalid_input`
- `audio_tool_error`
- `profile_error`
- `backend_error`
- `xiaoyao_tts_error`
