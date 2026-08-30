#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
BLENDER="${BLENDER:-blender}"
BLEND="$ROOT/output/naoshima.blend"
if [[ ! -f "$BLEND" ]]; then
  echo "output/naoshima.blend missing; generating first..."
  "$BLENDER" --background --python "$ROOT/generate.py" -- --render-previews
else
  "$BLENDER" --background --python "$ROOT/generate.py" -- --render-previews
fi
