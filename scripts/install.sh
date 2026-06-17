#!/usr/bin/env bash
set -euo pipefail

MODE="all"
RUN_DOCTOR="1"

usage() {
  cat <<'EOF'
Install Xiaoyaozu TTS locally.

Usage:
  ./scripts/install.sh [--light|--tts|--all] [--skip-doctor]

Modes:
  --light       Install lightweight CLI only.
  --tts         Install CLI + VoxCPM runtime.
  --all         Install full developer/runtime environment. Default.

Options:
  --skip-doctor Do not run xiaoyao-tts doctor after install.
  -h, --help    Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --light)
      MODE="light"
      ;;
    --tts)
      MODE="tts"
      ;;
    --all)
      MODE="all"
      ;;
    --skip-doctor)
      RUN_DOCTOR="0"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

cd "$(dirname "$0")/.."

find_python() {
  for candidate in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if (3, 10) <= sys.version_info < (3, 13) else 1)
PY
      then
        command -v "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON_BIN="$(find_python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "Python >=3.10,<3.13 is required. Install Python 3.11 or 3.12, then rerun this script." >&2
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required but was not found on PATH." >&2
  echo "macOS with Homebrew: brew install ffmpeg" >&2
  echo "After installing ffmpeg, rerun this script." >&2
  exit 1
fi

echo "Using Python: $PYTHON_BIN"
echo "Using ffmpeg: $(command -v ffmpeg)"

"$PYTHON_BIN" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip

case "$MODE" in
  light)
    python -m pip install -e .
    ;;
  tts)
    python -m pip install -e ".[tts]"
    ;;
  all)
    python -m pip install -e ".[all]"
    ;;
esac

if [[ "$RUN_DOCTOR" == "1" ]]; then
  xiaoyao-tts doctor
fi

cat <<'EOF'

Installed.

Activate later with:
  source .venv/bin/activate

Try:
  xiaoyao-tts profile list
EOF
