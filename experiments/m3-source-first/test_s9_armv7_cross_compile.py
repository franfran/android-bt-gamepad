#!/usr/bin/env python3
"""Cross-compile real S9 transformed C++ function slices to ARMv7 ELF32.

This proves ARM target code generation only. NOT Android Soong, ABI, or device readiness.
"""
import os
from pathlib import Path
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent

def main():
    with tempfile.TemporaryDirectory() as t:
        root=Path(t)
        generated=root/"s9-host.cc"
        env=dict(os.environ,RETROBOX_S9_EMIT_SOURCE=str(generated))
        subprocess.run(["python3",str(HERE/"test_compiled_s9_integration.py")],env=env,check=True)
        source=generated.read_text()
        if source.count("#include <cstdint>")!=1 or source.count("#include <cstddef>")!=1:
            raise AssertionError("Unexpected headers in extracted S9 C++ harness")
        source=source.replace("#include <cstdint>", "typedef unsigned int uint32_t;\ntypedef unsigned short uint16_t;\ntypedef unsigned char uint8_t;")
        source=source.replace("#include <cstddef>", "#define NULL 0")
        arm=root/"s9-armv7.o"
        (root/"s9-armv7.cc").write_text(source)
        subprocess.run(["clang++","--target=armv7a-none-eabi","-std=c++17",
                        "-ffreestanding","-fno-exceptions","-fno-rtti","-Wall","-Wextra",
                        "-Werror","-pedantic","-c",str(root/"s9-armv7.cc"),"-o",str(arm)],
                       check=True)
        header=subprocess.check_output(["readelf","-h",str(arm)],text=True)
        if "Class:                             ELF32" not in header or "Machine:                           ARM" not in header:
            raise AssertionError("Wrong ELF architecture: "+header)
        print("PASS S9 actual transformed source slices cross-compiled as ELF32 ARM (armv7a-none-eabi)")
        print("NO Android sysroot, no Soong build, no vendor ABI or device test")

if __name__=="__main__":main()
