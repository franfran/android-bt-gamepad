#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
CC=${CC:-clang}
for item in 'slow_normal 450 a.entered' 'slow_stall 3500 a.entered' 'fast 0 b.entered'; do
  read -r name delay marker <<< "$item"
  "$CC" --target=armv7a-linux-androideabi -marm -O2 -fPIC -shared -nostdlib -fuse-ld=lld -Wl,-soname,"$name.so" -DDELAY_MS="$delay" -DMARKER="\"/data/local/tmp/retrobox_stage3d_s7c3e/$marker\"" constructor.c -o "$name.so"
done
printf 'void *dlopen(const char *p,int f){return (void*)0;}\n' > .link_stub.c
"$CC" --target=armv7a-linux-androideabi -marm -shared -fPIC -nostdlib -fuse-ld=lld -Wl,-soname,libdl.so .link_stub.c -o .link_stub.so
"$CC" --target=armv7a-linux-androideabi -marm -O2 -fPIE -pie -nostdlib -fuse-ld=lld -Wl,-dynamic-linker,/system/bin/linker -Wl,--no-as-needed s7c3e.c ./.link_stub.so -o s7c3e_arm32
rm .link_stub.c .link_stub.so
file s7c3e_arm32 *.so
