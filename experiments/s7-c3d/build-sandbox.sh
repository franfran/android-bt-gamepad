#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
CC=${CC:-clang}
$CC --target=armv7a-linux-androideabi -marm -O2 -fPIC -shared -nostdlib -fuse-ld=lld -Wl,-soname,slow_normal.so -DDELAY_MS=450 -DMARKER='"/data/local/tmp/retrobox_stage3d_s7c3d/normal.entered"' slow_constructor.c -o slow_normal.so
$CC --target=armv7a-linux-androideabi -marm -O2 -fPIC -shared -nostdlib -fuse-ld=lld -Wl,-soname,slow_stall.so -DDELAY_MS=3500 -DMARKER='"/data/local/tmp/retrobox_stage3d_s7c3d/stall.entered"' slow_constructor.c -o slow_stall.so
printf 'void *dlopen(const char *p,int f){return (void*)0;}\n' > .link_stub.c
$CC --target=armv7a-linux-androideabi -marm -shared -fPIC -nostdlib -fuse-ld=lld -Wl,-soname,libdl.so .link_stub.c -o .link_stub.so
$CC --target=armv7a-linux-androideabi -marm -O2 -fPIE -pie -nostdlib -fuse-ld=lld -Wl,-dynamic-linker,/system/bin/linker -Wl,--no-as-needed s7c3d.c ./.link_stub.so -o s7c3d_arm32
rm .link_stub.c .link_stub.so
