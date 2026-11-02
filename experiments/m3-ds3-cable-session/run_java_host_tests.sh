#!/bin/sh
# Host-only Java contract test. No ADB, Android classpath, Bluetooth or USB.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT HUP INT TERM
javac -Xlint:all -Werror -d "$OUT" \
  "$HERE/Ds3AdmissionCoordinator.java" \
  "$HERE/TestDs3AdmissionCoordinator.java"
java -cp "$OUT" retrobox.TestDs3AdmissionCoordinator
