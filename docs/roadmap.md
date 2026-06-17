# Roadmap

## Phase 1: CLI MVP

- `xiaoyao-tts doctor`
- `xiaoyao-tts profile create`
- `xiaoyao-tts profile list`
- `xiaoyao-tts profile inspect`
- `xiaoyao-tts profile delete`
- `xiaoyao-tts speak`
- JSON output for agent calls
- Automatic audio conversion to 16kHz mono WAV
- Transcript caching inside voice profiles

## Phase 2: Agent Workflow

- Stable JSON schemas
- `--text-file` batch-friendly calls
- Better machine-readable error codes
- Optional daemon/server mode for faster repeated generation

## Phase 3: Minimal Web UI

- Voice library sidebar
- Add voice profile flow
- Target text input
- Generate and download output

## Phase 4: Packaging

- GitHub Actions checks
- Release artifacts
- `pipx` install path
- Optional macOS local app wrapper

## Later: Paid Features

Potential paid features can be layered without changing the local core:

- Profile packs and team sharing
- Queue/batch video dubbing workflow
- Commercial voice usage records
- Higher-performance server/daemon mode
- Studio UI, project history, and exports
