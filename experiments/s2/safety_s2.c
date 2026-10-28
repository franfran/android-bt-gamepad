/* Freestanding ARM EABI / Linux kernel syscall safety-harness, no NDK needed.
 * Owner-child only. 4 kernel threads in child via clone(2), one leader traced.
 * No target PID argument, no Bluetooth access, no injection, no memory pokes.
 */
#include <stdint.h>
typedef unsigned int u32;
typedef unsigned long size_t;
#define SYS_exit 1
#define SYS_write 4
#define SYS_wait4 114
#define SYS_kill 37
#define SYS_getpid 20
#define SYS_munmap 91
#define SYS_clone 120
#define SYS_ptrace 26
#define SYS_nanosleep 162
#define SYS_mmap2 192
#define SYS_clock_gettime 263
#define PTRACE_DETACH 17
#define PTRACE_CONT 7
#define PTRACE_GETREGS 12
#define PTRACE_SETREGS 13
#define SIGTRAP 5
#define PTRACE_SEIZE 0x4206
#define PTRACE_INTERRUPT 0x4207
#define MAP_SHARED 1
#define MAP_ANONYMOUS 0x20
#define PROT_READ 1
#define PROT_WRITE 2
#define CLONE_VM 0x100
#define CLONE_FS 0x200
#define CLONE_FILES 0x400
#define CLONE_SIGHAND 0x800
#define CLONE_THREAD 0x10000
#define CLONE_SYSVSEM 0x40000
#define SIGCHLD 17
#define SIGKILL 9
#define WNOHANG 1
#define __WALL 0x40000000
#define WORKERS 4
struct ts {long sec;long nsec;};
static inline long sc0(long n){register long r7 asm("r7")=n;register long r0 asm("r0"); asm volatile("svc #0":"=r"(r0):"r"(r7):"memory","cc");return r0;}
static inline long sc1(long n,long a){register long r7 asm("r7")=n;register long r0 asm("r0")=a;asm volatile("svc #0":"+r"(r0):"r"(r7):"memory","cc");return r0;}
static inline long sc2(long n,long a,long b){register long r7 asm("r7")=n;register long r0 asm("r0")=a;register long r1 asm("r1")=b;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r7):"memory","cc");return r0;}
static inline long sc3(long n,long a,long b,long c){register long r7 asm("r7")=n;register long r0 asm("r0")=a;register long r1 asm("r1")=b;register long r2 asm("r2")=c;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory","cc");return r0;}
static inline long sc4(long n,long a,long b,long c,long d){register long r7 asm("r7")=n;register long r0 asm("r0")=a;register long r1 asm("r1")=b;register long r2 asm("r2")=c;register long r3 asm("r3")=d;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r7):"memory","cc");return r0;}
static inline long sc5(long n,long a,long b,long c,long d,long e){register long r7 asm("r7")=n;register long r0 asm("r0")=a;register long r1 asm("r1")=b;register long r2 asm("r2")=c;register long r3 asm("r3")=d;register long r4 asm("r4")=e;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r4),"r"(r7):"memory","cc");return r0;}
static inline long sc6(long n,long a,long b,long c,long d,long e,long f){register long r7 asm("r7")=n;register long r0 asm("r0")=a;register long r1 asm("r1")=b;register long r2 asm("r2")=c;register long r3 asm("r3")=d;register long r4 asm("r4")=e;register long r5 asm("r5")=f;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r4),"r"(r5),"r"(r7):"memory","cc");return r0;}
static void out(const char*s){const char *p=s;while(*p)p++;sc3(SYS_write,1,(long)s,p-s);}
static void num(long x){char a[24];int i=23;a[i--]=0;if(x<0){out("-");x=-x;}do{a[i--]='0'+x%10;x/=10;}while(x);out(a+i+1);}
static void ms(long m){struct ts t={m/1000,(m%1000)*1000000};sc2(SYS_nanosleep,(long)&t,0);}
static long monotonic_ms(void){struct ts t; if(sc2(SYS_clock_gettime,1,(long)&t)<0)return -1;return t.sec*1000+t.nsec/1000000;}
struct shared {volatile u32 ready;volatile u32 ticks[WORKERS];};
static struct shared *S;
static volatile int keep_running=1;
static unsigned char stacks[WORKERS][16384] __attribute__((aligned(16)));
__attribute__((used,noinline)) static void worker(long index){__sync_add_and_fetch(&S->ready,1);while(keep_running){__sync_add_and_fetch(&S->ticks[index],1);ms(10);} sc1(SYS_exit,0);for(;;);}
/* Switch child clone return directly into worker() using synthetic stack. */
__attribute__((naked)) static long launch_thread(long flags,long stack,long idx){
 asm volatile(
 "push {r4,lr}\n"
 "mov r4, r2\n"
 "mov r2, #0\n"
 "mov r3, #0\n"
 "mov r7, #120\n"
 "svc #0\n"
 "cmp r0, #0\n"
 "bne 1f\n"
 "mov r0, r4\n"
 "bl worker\n"
 "mov r0, #0\n"
 "mov r7, #1\n"
 "svc #0\n"
 "1: pop {r4,pc}\n"
 );
}
static void child_run(void){
 for(long i=0;i<WORKERS;i++){
   long top=(long)&stacks[i][sizeof(stacks[i])];
   long r=launch_thread(CLONE_VM|CLONE_FS|CLONE_FILES|CLONE_SIGHAND|CLONE_THREAD|CLONE_SYSVSEM,top,i);
   if(r<0) sc1(SYS_exit,80);
 }
 while(1)ms(30);
}
static int status_stopped(long st);
/* All three probe functions are ARM-state and require no stack use.
 * Code is resident in the fork-owned child; no code/data memory writes.
 */
__attribute__((naked,used,noinline)) static void remote_fast(void){
 asm volatile("add r0, r0, #7\n" "bx lr\n");
}
__attribute__((naked,used,noinline)) static void remote_spin(void){
 asm volatile("1: b 1b\n");
}
__attribute__((naked,used,noinline)) static void return_trap(void){
 asm volatile("bkpt #0\n" "bx lr\n");
}
struct arm_regs {u32 r[18];}; /* r0-r15, CPSR, ORIG_R0 */
static void copyregs(struct arm_regs *to,const struct arm_regs *from){for(int i=0;i<18;i++)to->r[i]=from->r[i];}
static long wait_stop_reason(long pid,long timeout_ms,long *status){
 long deadline=monotonic_ms()+timeout_ms;
 while(monotonic_ms()<deadline){
  long r=sc4(SYS_wait4,pid,(long)status,WNOHANG|__WALL,0);
  if(r==pid)return status_stopped(*status)?1:-2;
  if(r<0)return r;
  ms(10);
 }
 return 0;
}
static int remote_call(long pid,const struct arm_regs *original,u32 function,u32 argument,int expect_timeout){
 struct arm_regs call,stopped;
 long st=0;copyregs(&call,original);
 call.r[0]=argument;
 call.r[14]=(u32)(uintptr_t)return_trap;
 call.r[15]=function&~1u;
 call.r[16]=(call.r[16]&~0x20u)|((function&1u)?0x20u:0);
 call.r[17]=0xffffffffu;
 if(sc4(SYS_ptrace,PTRACE_SETREGS,pid,0,(long)&call)<0){out("FAIL: PTRACE_SETREGS\n");return 0;}
 if(sc4(SYS_ptrace,PTRACE_CONT,pid,0,0)<0){out("FAIL: PTRACE_CONT\n");return 0;}
 long w=wait_stop_reason(pid,expect_timeout?250:1000,&st);
 if(expect_timeout){
  if(w!=0){out("FAIL: stall unexpectedly stopped before timeout\n");return 0;}
  out("REMOTE CALL TIMEOUT CONFIRMED (250ms)\n");
  if(sc4(SYS_ptrace,PTRACE_INTERRUPT,pid,0,0)<0){out("FAIL: PTRACE_INTERRUPT after timeout\n");return 0;}
  w=wait_stop_reason(pid,1000,&st);
  if(w!=1){out("FAIL: timeout interrupt did not stop child\n");return 0;}
  out("TIMEOUT CHILD INTERRUPTED OK\n");
 }else{
  if(w!=1){out("FAIL: return trap not observed\n");return 0;}
  int sig=(st>>8)&255;
  if(sig!=SIGTRAP){out("FAIL: wrong remote call stop signal=");num(sig);out("\n");return 0;}
  if(sc4(SYS_ptrace,PTRACE_GETREGS,pid,0,(long)&stopped)<0){out("FAIL: return GETREGS\n");return 0;}
  if(stopped.r[0]!=argument+7){out("FAIL: return value mismatch\n");return 0;}
  out("REMOTE FUNCTION RETURN OK r0=");num(stopped.r[0]);out("\n");
 }
 if(sc4(SYS_ptrace,PTRACE_SETREGS,pid,0,(long)original)<0){out("FAIL: register restore\n");return 0;}
 if(sc4(SYS_ptrace,PTRACE_GETREGS,pid,0,(long)&stopped)<0){out("FAIL: register verify GETREGS\n");return 0;}
 for(int i=0;i<18;i++)if(stopped.r[i]!=original->r[i]){out("FAIL: register restore mismatch\n");return 0;}
 out("REGISTERS RESTORED AND VERIFIED\n");
 return 1;
}
static int status_stopped(long st){return (st&255)==0x7f;}
static int waitstop(long pid,long*st){long deadline=monotonic_ms()+1500;while(monotonic_ms()<deadline){long r=sc4(SYS_wait4,pid,(long)st,WNOHANG|__WALL,0);if(r==pid)return status_stopped(*st);if(r<0)return 0;ms(10);}return 0;}
static void cleanup(long pid,int seized){
 if(seized){long r=sc4(SYS_ptrace,PTRACE_INTERRUPT,pid,0,0);(void)r;long wst=0;(void)wait_stop_reason(pid,200,&wst);r=sc4(SYS_ptrace,PTRACE_DETACH,pid,0,0);if(r==0)out("CLEANUP: DETACH OK\n");else out("CLEANUP: DETACH FAILED; kill owned child\n");}
 sc2(SYS_kill,pid,SIGKILL);
 long deadline=monotonic_ms()+2000,st=0;
 while(monotonic_ms()<deadline){long r=sc4(SYS_wait4,pid,(long)&st,WNOHANG,0);if(r==pid||r==-10){out("CLEANUP: OWNED CHILD REAPED\n");return;}ms(10);}
 out("CLEANUP WARNING: child reap timed out\n");
}
static int main_safety(void){
 out("RetroBox Stage 3D S2: ARM32 freestanding multi-thread safety harness\n");
 out("Owned multithread child only; NO Bluetooth / dlopen / memory writes\n");
 long mmap_result=sc6(SYS_mmap2,0,4096,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_ANONYMOUS,-1,0);
 /* ARM32 userspace mappings above 0x80000000 are valid. Linux only
  * indicates errno with unsigned syscall returns in 0xfffff001..ffffffff.
  */
 if((u32)mmap_result >= (u32)-4095){
   out("FAIL: shared mmap syscall errno=");num(-(int32_t)mmap_result);out("\n");return 1;
 }
 S=(void*)(uintptr_t)(u32)mmap_result;
 out("SHARED MMAP OK\n");
 S->ready=0;for(int i=0;i<WORKERS;i++)S->ticks[i]=0;
 long pid=sc5(SYS_clone,SIGCHLD,0,0,0,0);
 if(pid==0){child_run();sc1(SYS_exit,0);}
 if(pid<0){out("FAIL: fork via clone\n");return 1;}
 out("OWNED CHILD PID=");num(pid);out("\n");
 int seized=0,rc=1;long st=0,deadline=monotonic_ms()+3000;
 while(S->ready<WORKERS && monotonic_ms()<deadline)ms(10);
 if(S->ready!=WORKERS){out("FAIL: worker startup timeout, ready=");num(S->ready);out("\n");goto done;}
 out("WORKERS READY=4\n");
 u32 before[WORKERS];for(int i=0;i<WORKERS;i++)before[i]=S->ticks[i];
 if(sc4(SYS_ptrace,PTRACE_SEIZE,pid,0,0)<0){out("FAIL: PTRACE_SEIZE\n");goto done;}
 seized=1;out("PTRACE_SEIZE OK\n");
 if(sc4(SYS_ptrace,PTRACE_INTERRUPT,pid,0,0)<0){out("FAIL: PTRACE_INTERRUPT\n");goto done;}
 if(!waitstop(pid,&st)){out("FAIL: stop wait timed out/unexpected\n");goto done;}
 out("PTRACE_INTERRUPT STOP OK\n");
 struct arm_regs saved;
 if(sc4(SYS_ptrace,PTRACE_GETREGS,pid,0,(long)&saved)<0){out("FAIL: GETREGS\n");goto done;}
 out("PTRACE_GETREGS OK\n");
 if(!remote_call(pid,&saved,(u32)(uintptr_t)remote_fast,35,0))goto done;
 if(!remote_call(pid,&saved,(u32)(uintptr_t)remote_spin,0,1))goto done;
 if(sc4(SYS_ptrace,PTRACE_DETACH,pid,0,0)<0){out("FAIL: PTRACE_DETACH\n");goto done;}
 seized=0;out("PTRACE_DETACH OK\n");
 deadline=monotonic_ms()+2000;int advanced=0;
 while(monotonic_ms()<deadline){advanced=0;for(int i=0;i<WORKERS;i++)if(S->ticks[i]>before[i])advanced++;if(advanced==WORKERS)break;ms(10);}
 out("WORKERS PROGRESSED=");num(advanced);out("/4\n");
 if(advanced!=WORKERS){out("FAIL: thread progress\n");goto done;}
 out("PASS: isolated bounded remote call + timeout interrupt + register restore\n");rc=0;
done: cleanup(pid,seized);sc2(SYS_munmap,(long)S,4096);return rc;
}
__attribute__((noreturn)) void _start(void){int rc=main_safety();sc1(SYS_exit,rc);__builtin_unreachable();}
/* Runtime division helpers for freestanding ARM EABI, no libgcc needed. */
unsigned __aeabi_uidiv(unsigned n,unsigned d){unsigned q=0; if(!d)return 0; for(int i=31;i>=0;i--){if((n>>i)>=d && d<=(0xffffffffu>>i)){n-=d<<i;q|=1u<<i;}}return q;}
int __aeabi_idiv(int n,int d){if(!d)return 0;unsigned a=n<0?-(unsigned)n:(unsigned)n,b=d<0?-(unsigned)d:(unsigned)d;unsigned q=__aeabi_uidiv(a,b);return ((n<0)^(d<0))?-(int)q:(int)q;}
