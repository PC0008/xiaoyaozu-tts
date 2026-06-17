# Installation

逍遥族TTS 分成轻量核心和完整 TTS 运行环境。

## Requirements

- Python `>=3.10,<3.13`
- `ffmpeg` on PATH
- Apple Silicon/MPS, CUDA, or CPU runtime

macOS:

```bash
brew install ffmpeg
```

如果没有 Homebrew，也可以使用已有的 `ffmpeg` 二进制，只要 `xiaoyao-tts doctor` 能找到它即可。

## Developer Install

```bash
git clone https://github.com/PC0008/xiaoyaozu-tts.git
cd xiaoyaozu-tts

./scripts/install.sh --all
```

Manual equivalent:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"

xiaoyao-tts doctor
```

## Lightweight Install

只安装档案管理、历史、批量解析等轻量能力：

```bash
pip install -e .
```

这不会安装 VoxCPM。运行 `speak` 或自动 ASR 时需要完整安装：

```bash
pip install -e ".[tts]"
```

## Local Data

默认数据目录：

```text
~/.xiaoyaozu-tts/
  profiles/
  outputs/
  history/generations.jsonl
```

覆盖位置：

```bash
export XIAOYAO_TTS_HOME=/path/to/data
```

## First Run Notes

第一次自动转写会下载 SenseVoiceSmall。

第一次生成语音会下载 VoxCPM2。模型较大，后续会复用本机缓存。
