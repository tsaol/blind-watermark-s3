#!/bin/bash
set -e

LAYER_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="${LAYER_DIR}/output"

rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}/python"

echo "Installing dependencies..."
pip install numpy opencv-python-headless Pillow \
    --target "${OUTPUT_DIR}/python" \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.12 \
    --quiet

# Clean up to reduce size
find "${OUTPUT_DIR}" -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
find "${OUTPUT_DIR}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "${OUTPUT_DIR}" -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true
find "${OUTPUT_DIR}" -name "*.pyc" -delete 2>/dev/null || true

echo "Layer size: $(du -sh ${OUTPUT_DIR} | cut -f1)"

cd "${OUTPUT_DIR}"
zip -r9 "${LAYER_DIR}/layer.zip" python/
echo "Created: ${LAYER_DIR}/layer.zip ($(du -sh ${LAYER_DIR}/layer.zip | cut -f1))"
