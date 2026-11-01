#!/usr/bin/env bash
# RetroBox M3 Android 12 source-first build host provisioning (Ubuntu 22.04)
# Installs host packages ONLY. Does not clone large BSP source, build, flash or touch M3.
set -euo pipefail
if ! command -v apt-get >/dev/null; then
  echo "ERROR: requires Ubuntu/Debian apt-get" >&2; exit 1
fi
if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "ERROR: x86_64 build host required" >&2; exit 1
fi
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git git-lfs git-core gnupg flex bison build-essential zip unzip curl wget \
  zlib1g-dev libc6-dev-i386 lib32z1-dev libgl1-mesa-dev libx11-dev \
  libxml2-utils xsltproc fontconfig python3 python3-pip \
  openjdk-11-jdk ccache rsync file binutils libssl-dev libncurses-dev \
  ca-certificates jq
echo "Host packages installed. No BSP checkout/build performed."
echo "Check: df -h; free -h; java -version; python3 --version"
