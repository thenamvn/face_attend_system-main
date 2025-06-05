#!/bin/bash

set -e

echo "??? Starting optimized Nuitka build (with JAX + pyenv fixed)..."

# Detect Python path
PYTHON_BIN=$(which python3)
PYTHON_DIR=$(dirname $(dirname $(realpath "$PYTHON_BIN")))

echo "?? Python in use: $PYTHON_BIN"
echo "?? Python root dir: $PYTHON_DIR"

# Export flags if using pyenv
if [[ "$PYTHON_BIN" == *".pyenv"* ]]; then
  echo "?? Detected pyenv Python — setting LDFLAGS and CFLAGS (with subdir)..."
  export CFLAGS="-I$PYTHON_DIR/include -I$PYTHON_DIR/include/python3.9 -Wno-error=unused-but-set-variable"
  export LDFLAGS="-L$PYTHON_DIR/lib -L$PYTHON_DIR/lib/python3.9/config-3.9-aarch64-linux-gnu"
fi

# Use gcc without ccache (fix for Nuitka on Pi)
export CC="gcc"
echo "? Using GCC (no ccache, for stability on Raspberry Pi)"

# Run Nuitka build
$PYTHON_BIN -m nuitka main_copy_pir.py \
  --standalone \
  --include-module=gpiozero \
  --include-module=gpiozero.pins.lgpio \
  --include-module=gpiozero.pins.rpigpio \
  --include-module=gpiozero.pins.native \
  --include-module=pigpio \
  --include-module=RPi.GPIO \
  --noinclude-unittest-mode=nofollow \
  --static-libpython=yes \
  --remove-output \
  --output-dir=build \
  --lto=yes \
  --jobs=4 \
  --debug \
  --show-scons \
  --include-data-dir=face_database=face_database \
  --include-data-dir=model=model \
  --include-data-dir=fonts=fonts \
  --module-parameter=torch-disable-jit=yes

echo ""
echo "? Build complete!"
echo "?? To run: cd build/main_copy_pir.dist && ./main_copy_pir"

echo ""
echo "?? CCache summary:"
ccache -s || echo "ccache not in use"
