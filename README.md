# 逍遥族TTS

本地优先的声音克隆工具，面向创作者和 Agent 工作流。

当前阶段：CLI MVP 开发中。

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

xiaoyao-tts doctor
```

创建声音档案：

```bash
xiaoyao-tts profile create \
  --name me \
  --audio ./me.m4a
```

如果你已经有参考音频文稿，可以跳过自动识别：

```bash
xiaoyao-tts profile create \
  --name me \
  --audio ./me.m4a \
  --transcript "这是一段参考录音的文字内容。"
```

生成配音：

```bash
xiaoyao-tts speak \
  --profile me \
  --text "大家好，今天我们来分享一个主题。" \
  --out ./out.wav
```

给 Agent 调用时加 `--json`：

```bash
xiaoyao-tts profile list --json
xiaoyao-tts speak --profile me --text-file script.txt --out out.wav --json
```

修正参考音频文稿：

```bash
xiaoyao-tts profile update-transcript me \
  --transcript-file corrected-transcript.txt
```

查看生成历史：

```bash
xiaoyao-tts history list
xiaoyao-tts history list --profile me --json
```

批量生成：

```bash
# txt: 一行一条文案，空行和 # 注释会跳过
xiaoyao-tts batch \
  --profile me \
  --input scripts.txt \
  --out-dir outputs/batch

# jsonl: 每行一个 {"id": "...", "text": "..."}
xiaoyao-tts batch \
  --profile me \
  --input scripts.jsonl \
  --out-dir outputs/batch \
  --json
```

## Project Structure

```text
xiaoyaozu-tts/
  assets/brand/   Logo 与品牌资产
  docs/           产品和设计文档
  src/            CLI 与核心代码
  tests/          基础测试
```

## Brand Assets

- `assets/brand/xiaoyaozu-tts-logo.svg`
- `assets/brand/xiaoyaozu-tts-mark.svg`
- `docs/brand.md`

## Local Data

默认数据目录：

```text
~/.xiaoyaozu-tts/
  profiles/
  outputs/
  history/generations.jsonl
```

可以通过环境变量覆盖：

```bash
export XIAOYAO_TTS_HOME=/path/to/local/data
```
