# CLI Reference

## Check Environment

```bash
xiaoyao-tts doctor
xiaoyao-tts doctor --json
```

## Voice Profiles

Create with automatic ASR:

```bash
xiaoyao-tts profile create \
  --name me \
  --audio ./me.m4a
```

Create with a known transcript:

```bash
xiaoyao-tts profile create \
  --name me \
  --audio ./me.m4a \
  --transcript-file transcript.txt
```

List and inspect:

```bash
xiaoyao-tts profile list
xiaoyao-tts profile inspect me
```

Update transcript:

```bash
xiaoyao-tts profile update-transcript me \
  --transcript-file corrected-transcript.txt
```

Delete:

```bash
xiaoyao-tts profile delete me
```

## Single Generation

```bash
xiaoyao-tts speak \
  --profile me \
  --text "大家好，这是逍遥族TTS。" \
  --out outputs/demo.wav \
  --device mps
```

Useful options:

- `--text-file script.txt`
- `--device auto|cpu|mps|cuda|cuda:N`
- `--inference-timesteps 4`
- `--cfg-value 2.0`
- `--json`

## Batch Generation

TXT input:

```text
第一条文案。
第二条文案。
```

```bash
xiaoyao-tts batch \
  --profile me \
  --input examples/scripts.txt \
  --out-dir outputs/batch \
  --device mps
```

JSONL input:

```jsonl
{"id":"scene-01","text":"第一幕旁白。"}
{"id":"scene-02","text":"第二幕旁白。"}
```

```bash
xiaoyao-tts batch \
  --profile me \
  --input examples/scripts.jsonl \
  --out-dir outputs/batch \
  --format jsonl \
  --json
```

## History

```bash
xiaoyao-tts history list
xiaoyao-tts history list --profile me --limit 10 --json
```
