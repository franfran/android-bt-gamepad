#!/usr/bin/env bash
# Offline-only sanitized host tests. Distinct binaries prevent shadowed coverage.
set -euo pipefail
cd "$(dirname "$0")/../.."
tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/retrobox-s3-tests.XXXXXX")"
trap 'rm -rf "$tmpdir"' EXIT
for name in test_transaction_owner test_bta_w4_overwrite; do
  "${CXX:-c++}" -std=c++17 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    "experiments/m3-source-first/${name}.cc" -o "$tmpdir/$name"
  echo "RUN $name"
  "$tmpdir/$name"
done
