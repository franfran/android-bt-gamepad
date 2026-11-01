#!/usr/bin/env bash
# Offline host-only C++ test. Never connects to any Android device.
set -euo pipefail
cd "$(dirname "$0")/../.."
testbin="$(mktemp "${TMPDIR:-/tmp}/retrobox-s3-test.XXXXXX")"
trap 'rm -f "$testbin"' EXIT
"${CXX:-c++}" -std=c++17 -O1 -g -Wall -Wextra -Werror -pedantic \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  experiments/m3-source-first/test_transaction_owner.cc -o "$testbin"
"$testbin"
