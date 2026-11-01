#!/usr/bin/env python3
"""Reject incomplete trees before anyone tries a full Android build."""
from pathlib import Path
import subprocess
import tempfile
with tempfile.TemporaryDirectory() as t:
    p=subprocess.run(["python3",str(Path(__file__).with_name("full_bsp_build_preflight.py")),t],
                     capture_output=True,text=True)
    assert p.returncode == 1,p.stdout
    assert "NO_GO: missing: build/envsetup.sh" in p.stdout,p.stdout
    assert "No build executed." in p.stdout,p.stdout
print("PASS fail-closed preflight rejects empty/non-Android checkout")
