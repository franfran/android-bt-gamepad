/* S7-C4C non-fork, separately started ARM32 test target. NOT Bluetooth. */
typedef unsigned int u32;
extern void *dlopen(const char *,int);
extern char *dlerror(void);
#define WORKERS 48
#define FLAGS 0x50f00
static unsigned char stacks[WORKERS][8192] __attribute__((aligned(16)));
volatile u32 rbxc4c_ticks[WORKERS];
volatile u32 rbxc4c_ready;
static const char process_name[]="rbxc4c_target";
struct timespec_ {int sec,nsec;};
static inline int sys1(int n,int a){register int r0 asm("r0")=a,r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r7):"memory");return r0;}
static inline int sys2(int n,int a,int b){register int r0 asm("r0")=a,r1 asm("r1")=b,r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r7):"memory");return r0;}
static inline int sys3(int n,int a,int b,int c){register int r0 asm("r0")=a,r1 asm("r1")=b,r2 asm("r2")=c,r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory");return r0;}
static void sleep_ms(int m){struct timespec_ t={m/1000,(m%1000)*1000000};sys2(162,(int)&t,0);}
static void worker(int i) __attribute__((used,noinline));
static void worker(int i){__sync_add_and_fetch(&rbxc4c_ready,1);for(;;){__sync_add_and_fetch(&rbxc4c_ticks[i],1);sleep_ms(10);}}
__attribute__((naked)) static int spawn(int flags,int sp,int id){asm volatile(
 "push {r4,lr}\n mov r4,r2\n mov r2,#0\n mov r3,#0\n mov r7,#120\n svc #0\n cmp r0,#0\n bne 1f\n mov r0,r4\n bl worker\n mov r0,#0\n mov r7,#1\n svc #0\n 1: pop {r4,pc}\n");}
__attribute__((used,noinline,visibility("default"),naked)) void rbxc4c_return_trap(void){asm volatile("bkpt #0\n bx lr\n");}
__attribute__((used,noinline,visibility("default"),naked)) void rbxc4c_mmap2(void){asm volatile("mov r7,#192\n svc #0\n bx lr\n");}
__attribute__((used,noinline,visibility("default"),naked)) void rbxc4c_mprotect(void){asm volatile("mov r7,#125\n svc #0\n bx lr\n");}
__attribute__((used,noinline,visibility("default"),naked)) void rbxc4c_munmap(void){asm volatile("mov r7,#91\n svc #0\n bx lr\n");}
__attribute__((used,noinline,visibility("default"))) void *rbxc4c_load(const char *path){return dlopen(path,2);}
__attribute__((used,noinline,visibility("default"))) char *rbxc4c_error(void){return dlerror();}
__attribute__((noreturn)) void _start(void){
  if(sys2(172,15,(int)process_name)<0)sys1(1,31); /* PR_SET_NAME */
  rbxc4c_ready=0;
  for(int i=0;i<WORKERS;i++){
    if(spawn(FLAGS,(int)&stacks[i][8192],i)<0)sys1(1,32);
  }
  for(;;)sys1(29,0); /* pause; loader always uses distinct tracer */
}