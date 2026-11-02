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
python3 "$HERE/verify_h618_acl_epoch_observer.py"
python3 "$HERE/verify_h618_request_bound_callback.py"
python3 "$HERE/test_h618_request_bound_callback_patch.py"
"$CXX" -std=c++17 -Wall -Wextra -Werror -pedantic \
  "$HERE/test_usb_enrollment.cc" -o "$OUT/check_usb_enrollment"
"$OUT/check_usb_enrollment"
"$CXX" -std=c++17 -Wall -Wextra -Werror -pedantic \
  "$HERE/test_java_admission_bridge.cc" -o "$OUT/check_java_admission"
"$OUT/check_java_admission"
python3 "$HERE/test_h618_jni_candidate_cpp_patch.py"
"$CXX" -std=c++17 -Wall -Wextra -Werror -pedantic -pthread \
  "$HERE/test_candidate_uhid_fence.cc" -o "$OUT/check_candidate_fence"
"$OUT/check_candidate_fence"
python3 "$HERE/verify_h618_uhid_lifecycle_v2.py"
