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
static const char pidfile[]="/data/local/tmp/retrobox_s7c4c_test/target.pid";
struct timespec_ {int sec,nsec;};
static inline int sys1(int n,int a){register int r0 asm("r0")=a,r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r7):"memory");return r0;}
static inline int sys2(int n,int a,int b){register int r0 asm("r0")=a,r1 asm("r1")=b,r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r7):"memory");return r0;}
static inline int sys3(int n,int a,int b,int c){register int r0 asm("r0")=a,r1 asm("r1")=b,r2 asm("r2")=c,r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory");return r0;}
/* Startup-only diagnostics; stdout is redirected to target.log by runner. */
static void mark(const char *s){int n=0;while(s[n])n++;sys3(4,1,(int)s,n);}
static void sleep_ms(int m){struct timespec_ t={m/1000,(m%1000)*1000000};sys2(162,(int)&t,0);}
/* PID is written by this ELF, not inferred from a transient Android sh $!.
 * O_WRONLY|O_CREAT|O_TRUNC on our fixed test path only; no general file IO. */
static int write_own_pid(void){
 int pid=sys1(20,0); /* ARM getpid */
 if(pid<=1)return 0;
 char digits[16],buffer[16];int n=0,k=0;
 do {digits[n++]=(char)('0'+pid%10);pid/=10;}while(pid>0&&n<14);
 while(n)buffer[k++]=digits[--n];buffer[k++]='\n';
 int fd=sys3(5,(int)pidfile,0x241,0600);
 if(fd<0)return 0;
 int written=sys3(4,fd,(int)buffer,k);
 int rc=sys1(6,fd);
 return written==k && rc==0;
}

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
/* Deliberate failure-path probes, only reachable in the fixed test ELF.
 * These never interact with Bluetooth or load any additional code. */
__attribute__((used,noinline,visibility("default"),noreturn))
void rbxc4c_fault_spin(void){
 for(;;)asm volatile("" ::: "memory");
}
__attribute__((used,noinline,visibility("default"),noreturn))
void rbxc4c_fault_signal(void){
 int pid=sys1(20,0); /* ARM getpid */
 int tid=sys1(224,0); /* ARM gettid */
 sys3(268,pid,tid,10); /* ARM tgkill(SIGUSR1) on the traced leader */
 for(;;)sys1(29,0); /* Fallback pause if signal is not delivered */
}
__attribute__((noreturn)) void _start(void){
  mark("TARGET STARTED\n");
  if(sys2(172,15,(int)process_name)<0){ /* PR_SET_NAME */
    mark("TARGET ERROR: PR_SET_NAME failed\n");
    sys1(1,31);
  }
  mark("TARGET PR_SET_NAME OK\n");
  if(!write_own_pid()){
    mark("TARGET ERROR: cannot write self PID file\n");
    sys1(1,33);
  }
  mark("TARGET SELF PIDFILE WRITTEN\n");
  rbxc4c_ready=0;
  for(int i=0;i<WORKERS;i++){
    if(spawn(FLAGS,(int)&stacks[i][8192],i)<0){
      mark("TARGET ERROR: worker clone failed\n");
      sys1(1,32);
    }
  }
  mark("TARGET 48 WORKERS SPAWNED\n");
  for(;;)sys1(29,0); /* pause; loader always uses distinct tracer */
}