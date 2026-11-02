#!/bin/sh
# Host-only descriptor envelope regression test (no ADB / Bluetooth / firmware).
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT HUP INT TERM
CXX=${CXX:-g++}
"$CXX" -std=c++17 -Wall -Wextra -Werror -pedantic \
  "$HERE/session_descriptor_envelope.cc" \
  "$HERE/test_session_descriptor_envelope.cc" -o "$OUT/check"
"$OUT/check"
