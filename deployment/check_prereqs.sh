#!/usr/bin/env bash
set -euo pipefail

missing=()
need() { command -v "$1" >/dev/null 2>&1 || missing+=("$1"); }

need bash
need sf
need python3
need awk
need sed
need grep
need sha256sum
need tee
need sort
need wc
need tr
need find
need mv
need cp
need rm
need mkdir
need date

if [[ "${#missing[@]}" -gt 0 ]]; then
  echo "❌ Prérequis manquants: ${missing[*]}"
  exit 1
fi
echo "✅ Prérequis OK"
