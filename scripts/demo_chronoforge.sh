#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO="$ROOT/examples/chronoforge-demo"

echo "==> Running current demo tests"
(
  cd "$DEMO"
  pytest
)

echo
echo "==> Starting ChronoForge on the demo workspace"
export LR_AGENT_WORKSPACE="$DEMO"
lr-agent chrono \
  "Keep current client configuration behavior stable while allowing future configuration evolution" \
  --generations 3 \
  --trajectories 3
