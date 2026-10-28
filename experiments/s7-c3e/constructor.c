/* ARM32 Bionic shared object: self-contained constructor latency probe.
 * Deliberately NO Bluetooth code or external dependencies. */
typedef unsigned int u32;
static inline int sc2(int n,int a,int b){register int r0 asm("r0")=a;register int r1 asm("r1")=b;register int r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r7):"memory");return r0;}
static inline int sc3(int n,int a,int b,int c){register int r0 asm("r0")=a;register int r1 asm("r1")=b;register int r2 asm("r2")=c;register int r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory");return r0;}
struct timespec32 {int sec,nsec;};
#ifndef DELAY_MS
#define DELAY_MS 450
#endif
#ifndef MARKER
#define MARKER "/data/local/tmp/retrobox_stage3d_s7c3d/normal.entered"
#endif
__attribute__((constructor)) static void on_load(void){
 const char *p=MARKER;
 int fd=sc3(5,(int)p,0x241 /* O_WRONLY|O_CREAT|O_TRUNC */,0600);
 if(fd>=0){char v='1';sc3(4,fd,(int)&v,1);sc2(6,fd,0);}
 struct timespec32 t={DELAY_MS/1000,(DELAY_MS%1000)*1000000};sc2(162,(int)&t,0);
}
int retrobox_marker(void){return 0x53433744;}
