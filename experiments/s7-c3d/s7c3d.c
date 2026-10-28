/* RetroBox S7-C3d isolated loader latency / fail-closed test.
 * Only fork-owned processes. No ptrace, remote dlopen or Bluetooth interaction.
 * 4 raw-clone workers use syscalls only; child leader uses dlopen. */
typedef unsigned int u32;
extern void *dlopen(const char *, int);
static const char normal_lib[]="/data/local/tmp/retrobox_stage3d_s7c3d/slow_normal.so";
static const char stall_lib[]="/data/local/tmp/retrobox_stage3d_s7c3d/slow_stall.so";
static const char normal_marker[]="/data/local/tmp/retrobox_stage3d_s7c3d/normal.entered";
static const char stall_marker[]="/data/local/tmp/retrobox_stage3d_s7c3d/stall.entered";
static inline int sc1(int n,int a){register int r0 asm("r0")=a;register int r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r7):"memory");return r0;}
static inline int sc2(int n,int a,int b){register int r0 asm("r0")=a;register int r1 asm("r1")=b;register int r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r7):"memory");return r0;}
static inline int sc3(int n,int a,int b,int c){register int r0 asm("r0")=a;register int r1 asm("r1")=b;register int r2 asm("r2")=c;register int r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory");return r0;}
static inline int sc4(int n,int a,int b,int c,int d){register int r0 asm("r0")=a;register int r1 asm("r1")=b;register int r2 asm("r2")=c;register int r3 asm("r3")=d;register int r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r7):"memory");return r0;}
static inline int sc6(int n,int a,int b,int c,int d,int e,int f){register int r0 asm("r0")=a;register int r1 asm("r1")=b;register int r2 asm("r2")=c;register int r3 asm("r3")=d;register int r4 asm("r4")=e;register int r5 asm("r5")=f;register int r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r4),"r"(r5),"r"(r7):"memory","cc");return r0;}
#define WORKERS 4
#define CLONE_FLAGS 0x50f00 /* VM|FS|FILES|SIGHAND|THREAD|SYSVSEM */
struct timespec32 {int sec,nsec;};
struct shared {volatile u32 ready;volatile u32 ticks[WORKERS];volatile u32 done;volatile u32 success;};
static struct shared *sh;
static unsigned char stacks[WORKERS][16384] __attribute__((aligned(16)));
static void worker(int i) __attribute__((used,noinline));
static void worker(int i){__sync_add_and_fetch(&sh->ready,1);for(;;){__sync_add_and_fetch(&sh->ticks[i],1);struct timespec32 t={0,12000000};sc2(162,(int)&t,0);}}
__attribute__((naked)) static int spawn_worker(int flags,int stack,int i){asm volatile("push {r4,lr}\n mov r4,r2\n mov r2,#0\n mov r3,#0\n mov r7,#120\n svc #0\n cmp r0,#0\n bne 1f\n mov r0,r4\n bl worker\n mov r0,#0\n mov r7,#1\n svc #0\n 1: pop {r4,pc}\n");}
static void msleep(int m){struct timespec32 t={m/1000,(m%1000)*1000000};sc2(162,(int)&t,0);}
static int millis(void){struct timespec32 t;if(sc2(263,1,(int)&t)<0)return -1;return t.sec*1000+t.nsec/1000000;}
static void out(const char*s){int n=0;while(s[n])++n;sc3(4,1,(int)s,n);}
static int exists(const char*p){int fd=sc3(5,(int)p,0,0);if(fd<0)return 0;sc1(6,fd);return 1;}
static void unlink_file(const char*p){sc1(10,(int)p);}
static int all_progressed(const u32 *prior){for(int i=0;i<WORKERS;i++)if(sh->ticks[i]<=prior[i])return 0;return 1;}
__attribute__((noreturn)) static void die(int code){sc1(1,code);for(;;){}}
static int scenario(const char*lib,const char*marker,int timeout_ms,int should_finish){
 unlink_file(marker);sh->ready=0;sh->done=0;sh->success=0;
 for(int i=0;i<WORKERS;i++)sh->ticks[i]=0;
 int pid=sc1(2,0);
 if(pid==0){
  for(int i=0;i<WORKERS;i++)if(spawn_worker(CLONE_FLAGS,(int)&stacks[i][16384],i)<0)die(51);
  while(sh->ready!=WORKERS)msleep(5);
  void *h=dlopen(lib,2); /* child leader, not remotely called */
  sh->success=(h!=0);sh->done=1;
  for(;;)sc1(29,0);
 }
 if(pid<0){out("FAIL: fork\n");return 0;}
 int ok=1;int ready=0;
 for(int i=0;i<200;i++){if(sh->ready==WORKERS){ready=1;break;}msleep(5);}
 if(!ready){out("FAIL: worker readiness\n");ok=0;goto cleanup;}
 out("WORKERS READY=4\n");
 int entered=0;
 for(int i=0;i<200;i++){if(exists(marker)){entered=1;break;}msleep(5);}
 if(!entered){out("FAIL: constructor entry not observed\n");ok=0;goto cleanup;}
 out("CONSTRUCTOR ENTRY OBSERVED\n");
 u32 before[WORKERS];for(int i=0;i<WORKERS;i++)before[i]=sh->ticks[i];
 int start=millis();
 while(!sh->done && millis()-start<timeout_ms)msleep(5);
 if(should_finish){
  if(sh->done && sh->success){out("DLOPEN COMPLETED AFTER CONSTRUCTOR DELAY\n");}
  else{out("FAIL: expected normal dlopen completion\n");ok=0;}
 }else{
  if(!sh->done){out("DEADLINE EXCEEDED DURING CONSTRUCTOR\n");out("STATE=QUARANTINE; SAFE_TO_RETRY=false\n");}
  else{out("FAIL: stall scenario completed before deadline\n");ok=0;}
 }
 if(all_progressed(before))out("WORKERS PROGRESSED=4/4\n");else{out("FAIL: worker progress\n");ok=0;}
 cleanup:
 sc2(37,pid,9); /* only fork-owned child */
 int st=0;sc4(114,pid,(int)&st,0,0);
 unlink_file(marker);
 out("OWNED CHILD TERMINATED AND REAPED\n");
 return ok;
}
static void run(void){
 out("RetroBox S7-C3d isolated constructor-stall / fail-closed probe\n");
 out("No Bluetooth attach; no remote dlopen; no external PID.\n");
 int addr=sc6(192,0,4096,3,1|0x20,-1,0);
 if((u32)addr>=0xfffff001u){out("FAIL: shared mmap\n");die(2);}
 sh=(struct shared*)addr;
 out("SCENARIO 1: bounded constructor delay\n");
 int normal=scenario(normal_lib,normal_marker,1800,1);
 out("SCENARIO 2: constructor exceeds deadline\n");
 int stalled=scenario(stall_lib,stall_marker,300,0);
 if(normal&&stalled)out("PASS: constructor-stall detection and fail-closed policy\n");
 else out("FAIL: S7-C3d probe did not pass\n");
 die(normal&&stalled?0:3);
}
__attribute__((noreturn)) void _start(void){run();die(99);}
