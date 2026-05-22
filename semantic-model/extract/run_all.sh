#!/usr/bin/env bash
# Full pipeline: extract → infer → (optionally enrich) → build model
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${1:-$SCRIPT_DIR/config.yaml}"

echo "=== Step 1: Extract catalog metadata ==="
python "$SCRIPT_DIR/extract_catalog.py" --config "$CONFIG"

echo ""
echo "=== Step 2: Infer relationships ==="
python "$SCRIPT_DIR/infer_relationships.py" "$CONFIG"

echo ""
echo "=== Step 3: Enrich descriptions (if enabled in config) ==="
python "$SCRIPT_DIR/enrich_descriptions.py" "$CONFIG"

echo ""
echo "=== Step 4: Build semantic model ==="
python "$SCRIPT_DIR/build_model.py" --config "$CONFIG"

echo ""
echo "Done! Semantic model is in: $(dirname "$CONFIG")/../model/"
