#!/bin/sh
# Host-only descriptor envelope and private-transport tests. No Bluetooth/ADB.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT HUP INT TERM
CXX=${CXX:-g++}
"$CXX" -std=c++17 -Wall -Wextra -Werror -pedantic \
  "$HERE/session_descriptor_envelope.cc" \
  "$HERE/test_session_descriptor_envelope.cc" -o "$OUT/check_envelope"
"$OUT/check_envelope"
"$CXX" -std=c++17 -Wall -Wextra -Werror -pedantic \
  "$HERE/session_descriptor_envelope.cc" \
  "$HERE/test_private_descriptor_transport.cc" -o "$OUT/check_transport"
"$OUT/check_transport"
