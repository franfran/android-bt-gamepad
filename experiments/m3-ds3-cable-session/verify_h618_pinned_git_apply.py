#!/usr/bin/env python3
"""Check disabled RetroBox H618 source overlays against *pinned Git blobs*.

Only downloads allowlisted public source files from an immutable upstream
commit, verifies each exact Git blob SHA-1, and runs git apply --check in a
temporary scratch directory. No Android build, device, ADB, root or patch
deployment. Requires HTTPS to raw.githubusercontent.com.

The tests are separate overlay profiles. Never combine UHID v1/v2/v3.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile
import urllib.error
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
PIN = "250eabfc529518b7f26432663ed0a867ab2f625d"
ORIGIN = "https://raw.githubusercontent.com/BPI-SINOVOIP/BPI-H618-Android12/"
BLOBS = {
    "system/bt/stack/btm/btm_sec.cc": "12181cec696bced4c4dfab72aaf328535b0cf39e",
    "system/bt/btif/src/btif_dm.cc": "49be64145eeebc3590086767dce09bb5999ef514",
    "system/bt/btif/co/bta_hh_co.cc": "c5aba4425d272dc963b6f60567d7b79fb0c18f75",
    "packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp": "074e39d5b024c921ca0c4ff3451cad732b40ded3",
    "packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java": "f1e974631c85bd86751d456221944a2a68f9567d",
}
PROFILES = {
    "auth": (
        "h618_legacy_auth_decision_trace_disabled.patch",
        ("system/bt/stack/btm/btm_sec.cc", "system/bt/btif/src/btif_dm.cc"),
    ),
    "jni": (
        "h618_jni_java_deny_only_disabled.patch",
        ("packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp",
         "packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java"),
    ),
    "uhid-v3": (
        "h618_uhid_provisional_v3_disabled.patch",
        ("system/bt/btif/co/bta_hh_co.cc",),
    ),
}


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") +
                        b"\x00" + data).hexdigest()


def fetch_pinned_source(rel: str) -> bytes:
    if rel not in BLOBS:
        raise ValueError("path not allowlisted: " + rel)
    url = ORIGIN + PIN + "/" + rel
    with urlopen(url, timeout=30) as response:
        # Never download unbounded content (BTM file is ~200k).
        data = response.read(2_000_001)
    if len(data) > 2_000_000:
        raise RuntimeError("upstream file unexpectedly large: " + rel)
    observed = blob_sha(data)
    if observed != BLOBS[rel]:
        raise RuntimeError("pinned upstream Git blob mismatch: " + rel +
                           " expected=" + BLOBS[rel] + " got=" + observed)
    print("PINNED_BLOB_PASS:", rel, observed, flush=True)
    return data


def apply_check(profile: str, cached: dict[str, bytes]):
    patch_name, source_paths = PROFILES[profile]
    with tempfile.TemporaryDirectory(prefix="retrobox-source-") as temp:
        root = Path(temp)
        for rel in source_paths:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(cached[rel])
        patch = HERE / patch_name
        if not patch.is_file():
            raise RuntimeError("missing committed patch: " + patch_name)
        # git apply --check reads the new source file diff but creates nothing.
        result = subprocess.run(
            ["git", "apply", "--check", str(patch)],
            cwd=root, text=True, capture_output=True,
        )
        if result.returncode:
            raise RuntimeError("git apply --check FAILED " + profile + ":\n" +
                               result.stderr.strip())
        print("GIT_APPLY_CHECK_PASS:", profile, patch_name, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=[*PROFILES, "all"], default="all")
    opts = parser.parse_args()
    selected = list(PROFILES) if opts.profile == "all" else [opts.profile]
    paths = dict.fromkeys(rel for name in selected
                          for rel in PROFILES[name][1])
    cached = {rel: fetch_pinned_source(rel) for rel in paths}
    for name in selected:
        apply_check(name, cached)
    print("SOURCE_PATCH_CHECKS_PASS:", ",".join(selected))
    print("NOT TESTED: Android Soong/ARM32 compile, binary ABI, M3 device")


if __name__ == "__main__":
    main()
