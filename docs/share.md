# Share And Agent Install

## Important: Private Repository Access

This repository is currently private:

```text
https://github.com/PC0008/xiaoyaozu-tts
```

Someone else can only clone it if one of these is true:

- You invite their GitHub account as a collaborator.
- Their agent has GitHub credentials with access to this private repo.
- You make the repository public later.
- You send them a ZIP/archive manually.

## Message To Send To A Friend Or Their Agent

Copy this:

```text
Please install this local CLI voice-cloning tool on my computer.

Repository:
https://github.com/PC0008/xiaoyaozu-tts

Steps:
1. Make sure Python 3.10, 3.11, or 3.12 is available.
2. Make sure ffmpeg is installed and available on PATH.
   - On macOS with Homebrew: brew install ffmpeg
3. Clone the repository:
   git clone https://github.com/PC0008/xiaoyaozu-tts.git
4. Enter the project folder:
   cd xiaoyaozu-tts
5. Run the installer:
   ./scripts/install.sh --all
6. Verify:
   source .venv/bin/activate
   xiaoyao-tts doctor

After installation, create a voice profile:
xiaoyao-tts profile create --name me --audio /path/to/my-recording.m4a

Generate speech:
xiaoyao-tts speak --profile me --text "Hello, this is a local test." --out outputs/test.wav --json
```

## Agent-Friendly Minimal Commands

If the agent already has GitHub access:

```bash
git clone https://github.com/PC0008/xiaoyaozu-tts.git
cd xiaoyaozu-tts
./scripts/install.sh --all
source .venv/bin/activate
xiaoyao-tts doctor --json
```

## Install Modes

```bash
./scripts/install.sh --light
```

Installs the lightweight CLI only. Useful for profile/history parsing tests.

```bash
./scripts/install.sh --tts
```

Installs the CLI and VoxCPM runtime.

```bash
./scripts/install.sh --all
```

Installs full runtime and development dependencies. Recommended for agents.

## First Real Run

The first automatic transcription downloads SenseVoiceSmall.

The first speech generation downloads VoxCPM2. The model is large, so the first run can take a while. Future runs reuse the local cache.
