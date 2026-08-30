#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
BLENDER="${BLENDER:-blender}"
if ! command -v "$BLENDER" >/dev/null 2>&1; then
  echo "Blender not found. Set BLENDER=/path/to/blender" >&2
  exit 1
fi
exec "$BLENDER" --background --python "$ROOT/generate.py" -- "$@"
