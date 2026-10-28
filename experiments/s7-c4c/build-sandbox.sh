#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
CC=${CC:-clang}
TARGET="--target=armv7a-linux-androideabi"
$CC $TARGET -marm -O2 -fPIC -shared -nostdlib -fuse-ld=lld -Wl,-soname,libretrobox_c4c_test.so test_addon.c -o libretrobox_c4c_test.so
printf 'void *dlopen(const char *p,int f){return (void*)0;} char *dlerror(void){return (void*)0;}\n' > .libdl.c
$CC $TARGET -marm -fPIC -shared -nostdlib -fuse-ld=lld -Wl,-soname,libdl.so .libdl.c -o .libdl.so
$CC $TARGET -marm -O2 -fPIE -pie -nostdlib -fuse-ld=lld -Wl,-dynamic-linker,/system/bin/linker -Wl,--export-dynamic -Wl,--no-as-needed target.c ./.libdl.so -o rbxc4c_target
rm -f .libdl.c .libdl.so
python3 - <<'PY'
import re,subprocess
raw=subprocess.check_output(['readelf','-Ws','rbxc4c_target'],text=True)
names=['rbxc4c_return_trap','rbxc4c_mmap2','rbxc4c_mprotect','rbxc4c_munmap','rbxc4c_load','rbxc4c_error','rbxc4c_ticks','rbxc4c_ready']
vals={}
for line in raw.splitlines():
    fields=line.split()
    if len(fields)>=8 and fields[-1] in names and fields[6]!='UND':
        vals[fields[-1]]=int(fields[1],16)
if set(vals)!=set(names):raise SystemExit('missing target symbols: '+str(set(names)-set(vals)))
with open('target_offsets.h','w') as f:
    f.write('/* GENERATED ONLY by build-sandbox.sh; binds to rbxc4c_target ELF. */\n')
    for n in names:f.write('#define OFF_'+n.upper()+' 0x%08Xu\n'%vals[n])
    f.write('#define RBXC4C_WORKERS 48\n')
print('target symbol RVAs:',{k:hex(v) for k,v in vals.items()})
PY
$CC $TARGET -marm -O2 -fPIE -pie -nostdlib -fuse-ld=lld -Wl,-dynamic-linker,/system/bin/linker controller.c -o rbxc4c_controller
readelf -h rbxc4c_target | grep -E 'Class:|Machine:|Type:'
readelf -h rbxc4c_controller | grep -E 'Class:|Machine:|Type:'