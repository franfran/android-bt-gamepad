/* RetroBox S7-C3e v2 concurrent loader timing / fail-closed test.
 * Only fork-owned processes. No ptrace, remote dlopen or Bluetooth interaction.
 * 4 raw-clone workers use syscalls only; child leader uses dlopen. */
typedef unsigned int u32;
extern void *dlopen(const char *, int);
static const char normal_marker[]="/data/local/tmp/retrobox_stage3d_s7c3d/normal.entered";
static const char stall_marker[]="/data/local/tmp/retrobox_stage3d_s7c3d/stall.entered";
static inline int sc1(int n,int a){register int r0 asm("r0")=a;register int r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r7):"memory");return r0;}
static inline int sc2(int n,int a,int b){register int r0 asm("r0")=a;register int r1 asm("r1")=b;register int r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r7):"memory");return r0;}
static inline int sc3(int n,int a,int b,int c){register int r0 asm("r0")=a;register int r1 asm("r1")=b;register int r2 asm("r2")=c;register int r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory");return r0;}
static inline int sc4(int n,int a,int b,int c,int d){register int r0 asm("r0")=a;register int r1 asm("r1")=b;register int r2 asm("r2")=c;register int r3 asm("r3")=d;register int r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r7):"memory");return r0;}
static inline int sc6(int n,int a,int b,int c,int d,int e,int f){register int r0 asm("r0")=a;register int r1 asm("r1")=b;register int r2 asm("r2")=c;register int r3 asm("r3")=d;register int r4 asm("r4")=e;register int r5 asm("r5")=f;register int r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r4),"r"(r5),"r"(r7):"memory","cc");return r0;}

#define WORKERS 4
#define CLONE_FLAGS 0x50f00
struct timespec32 {int sec,nsec;};
struct shared {volatile u32 ready, start_b, a_done, b_done, a_ok, b_ok; volatile u32 ticks[WORKERS];};
static struct shared *sh;
static unsigned char stacks[WORKERS][16384] __attribute__((aligned(16)));
static const char normal_lib[]="/data/local/tmp/retrobox_stage3d_s7c3e/slow_normal.so";
static const char stall_lib[]="/data/local/tmp/retrobox_stage3d_s7c3e/slow_stall.so";
static const char fast_lib[]="/data/local/tmp/retrobox_stage3d_s7c3e/fast.so";
static const char a_marker[]="/data/local/tmp/retrobox_stage3d_s7c3e/a.entered";
static const char b_marker[]="/data/local/tmp/retrobox_stage3d_s7c3e/b.entered";
static const char *target_a;
static int current_scenario;
static void msleep(int m){struct timespec32 t={m/1000,(m%1000)*1000000};sc2(162,(int)&t,0);}
static int millis(void){struct timespec32 t;if(sc2(263,1,(int)&t)<0)return -1;return t.sec*1000+t.nsec/1000000;}
static void out(const char*s){int n=0;while(s[n])++n;sc3(4,1,(int)s,n);}
static int exists(const char*p){int fd=sc3(5,(int)p,0,0);if(fd<0)return 0;sc1(6,fd);return 1;}
static void unlink_file(const char*p){sc1(10,(int)p);}
__attribute__((noreturn)) static void die(int code){sc1(1,code);for(;;){}}
static void worker(int i) __attribute__((used,noinline));
static void worker(int i){
 __sync_add_and_fetch(&sh->ready,1);
 if(i==0){void *h=dlopen(target_a,2);sh->a_ok=(h!=0);__sync_synchronize();sh->a_done=1;}
 else if(i==1){while(!sh->start_b)msleep(1);void *h=dlopen(fast_lib,2);sh->b_ok=(h!=0);__sync_synchronize();sh->b_done=1;}
 for(;;){__sync_add_and_fetch(&sh->ticks[i],1);msleep(10);}
}
__attribute__((naked)) static int spawn_worker(int flags,int stack,int i){asm volatile("push {r4,lr}\n mov r4,r2\n mov r2,#0\n mov r3,#0\n mov r7,#120\n svc #0\n cmp r0,#0\n bne 1f\n mov r0,r4\n bl worker\n mov r0,#0\n mov r7,#1\n svc #0\n 1: pop {r4,pc}\n");}
static int all_progressed(const u32 *prior){for(int i=2;i<WORKERS;i++)if(sh->ticks[i]<=prior[i])return 0;return 1;}
static int scenario(int stall){
 unlink_file(a_marker);unlink_file(b_marker);
 sh->ready=0;sh->start_b=0;sh->a_done=0;sh->b_done=0;sh->a_ok=0;sh->b_ok=0;
 for(int i=0;i<WORKERS;i++)sh->ticks[i]=0;
 target_a=stall?stall_lib:normal_lib;
 int pid=sc1(2,0);
 if(pid==0){
  for(int i=0;i<WORKERS;i++)if(spawn_worker(CLONE_FLAGS,(int)&stacks[i][16384],i)<0)die(51);
  for(;;)msleep(200);
 }
 if(pid<0){out("FAIL: fork\n");return 0;}
 int ok=1, ready=0;
 for(int i=0;i<300;i++){if(sh->ready==WORKERS){ready=1;break;}msleep(5);}
 if(!ready){out("FAIL: worker readiness\n");ok=0;goto cleanup;}
 out("WORKERS READY=4\n");
 int entered=0;
 for(int i=0;i<200;i++){if(exists(a_marker)){entered=1;break;}msleep(5);}
 if(!entered){out("FAIL: A constructor entry not observed\n");ok=0;goto cleanup;}
 out("A CONSTRUCTOR ENTERED; STARTING CONCURRENT B DLOPEN\n");
 u32 before[WORKERS];for(int i=0;i<WORKERS;i++)before[i]=sh->ticks[i];
 sh->start_b=1;
 int timeout=stall?300:1800, start=millis();
 int b_before_a=0;
 while(millis()-start<timeout){
  if(sh->b_done && !sh->a_done) b_before_a=1;
  if(!stall && sh->a_done && sh->b_done)break;
  msleep(5);
 }
 if(!stall){
  if(sh->a_done && sh->b_done && sh->a_ok && sh->b_ok && exists(b_marker)){
   if(b_before_a)out("OBSERVATION: B completed before A; constructors are not mutually serialized in this run\n");
   else out("OBSERVATION: A and B completed; B did not demonstrably precede A\n");
   out("NORMAL LOAD COMPLETE: both dlopen calls succeeded\n");
  }else {out("FAIL: both loads did not complete\n");ok=0;}
 }else{
  if(!sh->a_done){
   if(b_before_a)out("OBSERVATION: B completed while A constructor still running\n");
   else out("OBSERVATION: B not observed to complete before deadline\n");
   out("DEADLINE EXCEEDED WITH A IN CONSTRUCTOR\n");
   out("STATE=QUARANTINE; SAFE_TO_RETRY=false\n");
  }else {out("FAIL: A constructor finished before stall deadline\n");ok=0;}
 }
 /* Give background workers a fixed observation interval; the earlier test
    sampled immediately after B completed and made false-negative assertions. */
 msleep(120);
 if(all_progressed(before))out("BACKGROUND WORKERS PROGRESSED=2/2\n");else{out("FAIL: background worker progress after 120ms observation\n");ok=0;}
cleanup:
 sc2(37,pid,9);
 int st=0;sc4(114,pid,(int)&st,0,0);
 unlink_file(a_marker);unlink_file(b_marker);
 out("OWNED CHILD TERMINATED AND REAPED\n");
 return ok;
}
static void run(void){
 out("RetroBox S7-C3e: two-thread concurrent dlopen / linker contention probe\n");
 out("Fork-owned test child only. NO Bluetooth, ptrace, or remote calls.\n");
 int addr=sc6(192,0,4096,3,1|0x20,-1,0);
 if((u32)addr>=0xfffff001u){out("FAIL: shared mmap\n");die(2);}
 sh=(struct shared*)addr;
 out("SCENARIO 1: delayed constructor A and concurrent fast dlopen B\n");
 int normal=scenario(0);
 out("SCENARIO 2: stalled constructor A and concurrent B deadline\n");
 int stalled=scenario(1);
 if(normal&&stalled)out("PASS: isolated concurrent dlopen observations and fail-closed timeout\n");
 else out("FAIL: S7-C3e contention probe did not meet criteria\n");
 die(normal&&stalled?0:3);
}
__attribute__((noreturn)) void _start(void){run();die(99);}
