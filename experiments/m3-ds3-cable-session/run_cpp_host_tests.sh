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
"$CXX" -std=c++17 -Wall -Wextra -Werror -pedantic \
  "$HERE/session_descriptor_envelope.cc" \
  "$HERE/test_private_descriptor_wire.cc" -o "$OUT/check_wire"
"$OUT/check_wire"
"$CXX" -std=c++17 -Wall -Wextra -Werror -pedantic \
  "$HERE/session_descriptor_envelope.cc" \
  "$HERE/test_private_checked_dispatch.cc" -o "$OUT/check_checked"
"$OUT/check_checked"
python3 "$HERE/test_h618_checked_bytes_patch.py"
python3 "$HERE/test_h618_private_descriptor_probe_patch.py"
python3 "$HERE/test_h618_btm_auth_observe_patch.py"
"$CXX" -std=c++17 -Wall -Wextra -Werror -pedantic \
  "$HERE/test_acl_epoch_observer.cc" -o "$OUT/check_acl_epoch"
"$OUT/check_acl_epoch"
