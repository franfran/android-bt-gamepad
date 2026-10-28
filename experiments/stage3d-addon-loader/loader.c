/* Standalone ARM32 Android PIE with no libc or JNI dependency.
 * Calls platform libdl.so; stdout/error output through Linux write syscall.
 */
typedef unsigned int uint32_t;
extern void *dlopen(const char *, int);
extern void *dlsym(void *, const char *);
extern int dlclose(void *);
extern char *dlerror(void);
#define RTLD_NOW 2
#define RTLD_LOCAL 0
static long call_write(int fd, const void *p, unsigned len) {
  register long r0 __asm__("r0") = fd;
  register long r1 __asm__("r1") = (long)p;
  register long r2 __asm__("r2") = len;
  register long r7 __asm__("r7") = 4;
  __asm__ volatile("svc #0" : "+r"(r0) : "r"(r1),"r"(r2),"r"(r7) : "memory");
  return r0;
}
static void puts0(const char *s){ unsigned n=0; while(s[n])n++; (void)call_write(1,s,n); }
static void hex32(uint32_t x){char o[11]="0x00000000\n";const char *d="0123456789abcdef";for(int i=0;i<8;i++)o[2+i]=d[(x>>(28-4*i))&15];(void)call_write(1,o,11);}
static void quit(int code) {
  register long r0 __asm__("r0") = code;
  register long r7 __asm__("r7") = 1;
  __asm__ volatile("svc #0" :: "r"(r0),"r"(r7) : "memory");
  __builtin_unreachable();
}
static int run(void) {
  const char *path="/data/local/tmp/retrobox_stage3d/libretrobox_ds3_addon.so";
  puts0("RetroBox Stage 3D isolated loader (NOT Bluetooth injection)\n");
  void *h=dlopen(path,RTLD_NOW|RTLD_LOCAL);
  if(!h){puts0("DLOPEN FAIL: ");char *e=dlerror();puts0(e?e:"unknown error");puts0("\n");return 2;}
  puts0("DLOPEN OK\n");
  unsigned (*abi)(void)=(unsigned(*)(void))dlsym(h,"retrobox_addon_abi");
  unsigned (*probe)(unsigned)=(unsigned(*)(unsigned))dlsym(h,"retrobox_addon_probe");
  if(!abi||!probe){puts0("DLSYM FAIL\n");dlclose(h);return 3;}
  puts0("ABI: ");hex32(abi());
  unsigned v=probe(0x12345678u);
  puts0("Probe: ");hex32(v);
  if(v!=(0x12345678u^0x52425833u)){puts0("PROBE MISMATCH\n");dlclose(h);return 4;}
  int r=dlclose(h);
  puts0(r==0?"DLCLOSE OK\n":"DLCLOSE FAIL\n");
  return r==0?0:5;
}
__attribute__((noreturn)) void _start(void) { quit(run()); }
