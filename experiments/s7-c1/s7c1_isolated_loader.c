/* RetroBox S7-C1: isolated remote mmap + dlopen using fork-owned child ONLY.
 * Android ARM32, no libc dependency, no external PID input.
 * This program never accesses com.android.bluetooth.
 * SPDX-License-Identifier: MIT
 */
typedef unsigned int u32;
extern void *dlopen(const char *, int);
static const char path[]="/data/local/tmp/retrobox_stage3d_s7c1/libretrobox_ds3_addon.so";
static inline int sc1(int n,int a){register int r0 __asm__("r0")=a; register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r7):"memory");return r0;}
static inline int sc2(int n,int a,int b){register int r0 __asm__("r0")=a;register int r1 __asm__("r1")=b;register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r7):"memory");return r0;}
static inline int sc3(int n,int a,int b,int c){register int r0 __asm__("r0")=a;register int r1 __asm__("r1")=b;register int r2 __asm__("r2")=c;register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory");return r0;}
static inline int sc4(int n,int a,int b,int c,int d){register int r0 __asm__("r0")=a;register int r1 __asm__("r1")=b;register int r2 __asm__("r2")=c;register int r3 __asm__("r3")=d;register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r7):"memory");return r0;}

#define WORKERS 4
#define CLONE_VM 0x100
#define CLONE_FS 0x200
#define CLONE_FILES 0x400
#define CLONE_SIGHAND 0x800
#define CLONE_THREAD 0x10000
#define CLONE_SYSVSEM 0x40000
#define MAP_SHARED 1
#define MAP_ANONYMOUS 0x20
#define PROT_READ 1
#define PROT_WRITE 2
#define WNOHANG 1
#define WALL 0x40000000
struct time_spec {long sec;long nsec;};
static inline int sc5(int n,int a,int b,int c,int d,int e){register int r0 asm("r0")=a;register int r1 asm("r1")=b;register int r2 asm("r2")=c;register int r3 asm("r3")=d;register int r4 asm("r4")=e;register int r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r4),"r"(r7):"memory","cc");return r0;}
static inline int sc6(int n,int a,int b,int c,int d,int e,int f){register int r0 asm("r0")=a;register int r1 asm("r1")=b;register int r2 asm("r2")=c;register int r3 asm("r3")=d;register int r4 asm("r4")=e;register int r5 asm("r5")=f;register int r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r4),"r"(r5),"r"(r7):"memory","cc");return r0;}
static void sleep_ms(int m){struct time_spec t={m/1000,(m%1000)*1000000};(void)sc2(162,(int)&t,0);}
static int monotonic_ms(void){struct time_spec t;if(sc2(263,1,(int)&t)<0)return -1;return (int)(t.sec*1000+t.nsec/1000000);}
struct share {volatile unsigned ready; volatile unsigned ticks[WORKERS];};
static struct share *sh;
static unsigned char thread_stacks[WORKERS][16384] __attribute__((aligned(16)));
static void worker(int idx) __attribute__((used,noinline));
static void worker(int idx){__sync_add_and_fetch(&sh->ready,1);for(;;){__sync_add_and_fetch(&sh->ticks[idx],1);sleep_ms(12);}}
__attribute__((naked)) static int spawn_worker(int flags,int stack,int idx){
 asm volatile("push {r4,lr}\n mov r4, r2\n mov r2, #0\n mov r3, #0\n mov r7, #120\n svc #0\n cmp r0, #0\n bne 1f\n mov r0, r4\n bl worker\n mov r0, #0\n mov r7, #1\n svc #0\n 1: pop {r4,pc}\n");
}
static int worker_ready(void){return sh && sh->ready==WORKERS;}
static int workers_progressed(const unsigned *prior){for(int i=0;i<WORKERS;i++){if(sh->ticks[i]<=prior[i])return 0;}return 1;}

static void out(const char*s){int n=0;while(s[n])++n;(void)sc3(4,1,(int)s,n);}
static void hex(u32 v){char b[11]="0x00000000";const char*h="0123456789abcdef";for(int i=0;i<8;i++)b[2+i]=h[(v>>(28-4*i))&15];(void)sc3(4,1,(int)b,10);}
static void newline(void){out("\n");}
static void numdec(int a,char *b){char t[12];int n=0;unsigned v=a<0?-a:a;do{t[n++]=(char)('0'+v%10);v/=10;}while(v);int i=0;if(a<0)b[i++]='-';while(n)b[i++]=t[--n];b[i]=0;}
static int has(const char *s,int n,const char *q){int m=0;while(q[m])m++;for(int i=0;i+m<=n;i++){int j=0;while(j<m&&s[i+j]==q[j])j++;if(j==m)return 1;}return 0;}
static int maps_contains(int pid){char file[80]="/proc/"; char d[16]; numdec(pid,d);int i=6,j=0;while(d[j])file[i++]=d[j++];const char *tail="/maps";j=0;while(tail[j])file[i++]=tail[j++];file[i]=0;
 int fd=sc3(5,(int)file,0,0);if(fd<0)return -1;char buf[4096];int n;int found=0;char carry[128];int tailn=0;
 while((n=sc3(3,fd,(int)buf,4096))>0){if(has(buf,n,"libretrobox_ds3_addon.so")){found=1;break;}char temp[256];int k=0;for(int x=0;x<tailn;x++)temp[k++]=carry[x];int c=n<128?n:128;for(int x=0;x<c;x++)temp[k++]=buf[x];if(has(temp,k,"libretrobox_ds3_addon.so")){found=1;break;} tailn=n<128?n:128;for(int x=0;x<tailn;x++)carry[x]=buf[n-tailn+x];}
 (void)sc1(6,fd);return found;
}
/* Raw child-side ARM32 syscall. Six syscall args via r0-r5. */
__attribute__((naked,noinline,used)) static void remote_mmap2(void){
 __asm__ volatile("mov r7, #192\n svc #0\n bx lr\n");
}
__attribute__((naked,noinline,used)) static void remote_munmap(void){
 __asm__ volatile("mov r7, #91\n svc #0\n bx lr\n");
}
static int remote_poke(int pid,u32 addr,u32 val){return sc4(26,5,pid,(int)addr,(int)val)==0;}
static int remote_peek(int pid,u32 addr,u32 *val){u32 word=0;int rc=sc4(26,2,pid,(int)addr,(int)&word);if(rc!=0)return 0;*val=word;return 1;}
__attribute__((naked,noinline,used)) static void return_trap(void){__asm__ volatile("bkpt #0");}
__attribute__((noreturn)) static void terminate(int code){(void)sc1(1,code);for(;;){}}
struct regs {u32 r[18];}; /* ARM user_regs: r0..r15, CPSR, ORIG_R0 */
static void _run(void){
 out("RetroBox S7-C1 isolated target-owned scratch + remote dlopen (fork-owned child only)\n");
 out("No Bluetooth process, no arbitrary PID, no authentication modifications.\n");
 int map=sc6(192,0,4096,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_ANONYMOUS,-1,0);
 if((unsigned)map>=0xfffff001u){out("FAIL: SHARED MMAP\n");terminate(2);}
 sh=(struct share*)map;
 for(int i=0;i<WORKERS;i++)sh->ticks[i]=0;
 sh->ready=0;
 int pid=sc1(2,0);
 if(pid==0){
    for(int i=0;i<WORKERS;i++){
       int flags=CLONE_VM|CLONE_FS|CLONE_FILES|CLONE_SIGHAND|CLONE_THREAD|CLONE_SYSVSEM;
       if(spawn_worker(flags,(int)&thread_stacks[i][sizeof(thread_stacks[i])],i)<0)terminate(51);
    }
    for(;;)(void)sc1(29,0);
 } /* child pause() forever until parent cleanup */
 if(pid<0){out("FORK FAILED\n");terminate(2);}
 out("CHILD CREATED pid=");hex((u32)pid);newline();
 int ready=0;
 for(int i=0;i<200;i++){if(worker_ready()){ready=1;break;}sleep_ms(10);}
 if(!ready){out("FAIL: WORKERS NOT READY\n");(void)sc2(37,pid,9);int ws=0;(void)sc4(114,pid,(int)&ws,0,0);terminate(4);}
 out("WORKERS READY=4\n");
 unsigned before[WORKERS]; for(int i=0;i<WORKERS;i++)before[i]=sh->ticks[i];
 int attached=0,rc=0,st=0,failed=1, stopped_flag=0,have_regs=0; u32 remote_page=0;
 rc=sc4(26,16,pid,0,0);
 if(rc<0){out("PTRACE_ATTACH FAIL errno=");hex((u32)-rc);newline();goto done;}
 attached=1;
 int attach_end=monotonic_ms()+1500;
 rc=0;
 while(monotonic_ms()<attach_end){int wr=sc4(114,pid,(int)&st,WNOHANG|WALL,0);if(wr==pid||wr<0){rc=wr;break;}sleep_ms(10);}
 if(rc!=pid || (st&255)!=127){out("WAIT ATTACH STOP FAIL\n");goto done;}
 stopped_flag=1;
 out("PTRACE_ATTACH OK\n");
 struct regs original, modified, stopped;
 rc=sc4(26,12,pid,0,(int)&original);
 if(rc<0){out("GETREGS FAIL errno=");hex((u32)-rc);newline();goto done;}
 out("PTRACE_GETREGS OK\n");have_regs=1;
 /* Set up a return-trapped function call into the OWNED child. All call
  * arguments live in registers; no path is written into child's stack. */
 u32 trap=(u32)return_trap;
 u32 fn=(u32)remote_mmap2;
 for(int i=0;i<18;i++)modified.r[i]=original.r[i];
 modified.r[0]=0;modified.r[1]=4096;modified.r[2]=3; /* RW */
 modified.r[3]=0x22; /* MAP_PRIVATE | MAP_ANONYMOUS */
 modified.r[4]=0xffffffffu;modified.r[5]=0;
 modified.r[15]=fn&~1u;modified.r[14]=trap;
 modified.r[16]=(modified.r[16]&~0x20u)|((fn&1u)?0x20u:0);
 modified.r[17]=0xffffffffu;
 rc=sc4(26,13,pid,0,(int)&modified);
 if(rc<0){out("REMOTE MMAP SETREGS FAIL\n");goto done;}
 rc=sc4(26,7,pid,0,0);if(rc<0){out("REMOTE MMAP CONT FAIL\n");goto done;}
 stopped_flag=0;
 int until=monotonic_ms()+1500; rc=0;
 while(monotonic_ms()<until){int wr=sc4(114,pid,(int)&st,WNOHANG|WALL,0);if(wr==pid||wr<0){rc=wr;break;}sleep_ms(10);}
 if(rc!=pid || (st&255)!=127){out("REMOTE MMAP TIMEOUT; CHILD TERMINATED\n");goto done;}
 stopped_flag=1;
 if(((st>>8)&255)!=5 || sc4(26,12,pid,0,(int)&stopped)<0){out("REMOTE MMAP TRAP FAIL\n");goto done;}
 remote_page=stopped.r[0];
 if(remote_page>=0xfffff001u || (remote_page&4095u)){out("REMOTE MMAP INVALID ADDRESS\n");goto done;}
 out("REMOTE MMAP2 OK: CHILD-PRIVATE SCRATCH\n");
 /* Write addon path into CHILD-OWNED SCRATCH and verify every word. */
 for(u32 off=0;off<sizeof(path);off+=4){
   u32 v=0,verify=0;
   for(int j=0;j<4;j++){u32 i=off+j;if(i<sizeof(path))v|=((u32)(unsigned char)path[i])<<(8*j);}
   if(!remote_poke(pid,remote_page+off,v)||!remote_peek(pid,remote_page+off,&verify)||verify!=v){out("REMOTE PATH WRITE/VERIFY FAIL\n");goto done;}
 }
 out("REMOTE CHILD SCRATCH PATH VERIFIED\n");
 /* The verified libc-style remote dlopen call uses only 2 arguments. */
 for(int i=0;i<18;i++)modified.r[i]=original.r[i];
 fn=(u32)dlopen;
 modified.r[0]=remote_page;modified.r[1]=2; /* RTLD_NOW */
 modified.r[15]=fn&~1u;modified.r[14]=trap;
 modified.r[16]=(modified.r[16]&~0x20u)|((fn&1u)?0x20u:0);
 modified.r[17]=0xffffffffu;
 if(sc4(26,13,pid,0,(int)&modified)<0){out("DLOPEN SETREGS FAIL\n");goto done;}
 out("REMOTE DLOPEN ARMED WITH CHILD-PRIVATE PATH\n");
 if(sc4(26,7,pid,0,0)<0){out("DLOPEN CONT FAIL\n");goto done;}
 stopped_flag=0;
 until=monotonic_ms()+3000; rc=0;
 while(monotonic_ms()<until){int wr=sc4(114,pid,(int)&st,WNOHANG|WALL,0);if(wr==pid||wr<0){rc=wr;break;}sleep_ms(10);}
 if(rc!=pid || (st&255)!=127){out("DLOPEN TIMEOUT; KILL OWNED CHILD (NO DETACH)\n");goto done;}
 stopped_flag=1;
 if(((st>>8)&255)!=5 || sc4(26,12,pid,0,(int)&stopped)<0){out("DLOPEN RETURN TRAP FAIL\n");goto done;}
 if(!stopped.r[0]){out("REMOTE DLOPEN NULL\n");goto done;}
 out("REMOTE DLOPEN NONNULL\n");
 rc=maps_contains(pid);
 if(rc!=1){out("ADDON NOT MAPPED IN CHILD\n");goto done;}
 out("ADDON MAPPED IN CHILD: YES\n");
 /* Release the scratch from within child, not from parent shared pages. */
 for(int i=0;i<18;i++)modified.r[i]=original.r[i];
 fn=(u32)remote_munmap;
 modified.r[0]=remote_page;modified.r[1]=4096;
 modified.r[15]=fn&~1u;modified.r[14]=trap;
 modified.r[16]=(modified.r[16]&~0x20u)|((fn&1u)?0x20u:0);
 modified.r[17]=0xffffffffu;
 if(sc4(26,13,pid,0,(int)&modified)<0 || sc4(26,7,pid,0,0)<0){out("MUNMAP CALL ARM FAIL\n");goto done;}
 stopped_flag=0;until=monotonic_ms()+1500;rc=0;
 while(monotonic_ms()<until){int wr=sc4(114,pid,(int)&st,WNOHANG|WALL,0);if(wr==pid||wr<0){rc=wr;break;}sleep_ms(10);}
 if(rc!=pid || (st&255)!=127){out("MUNMAP TIMEOUT\n");goto done;}
 stopped_flag=1;
 if(((st>>8)&255)!=5 || sc4(26,12,pid,0,(int)&stopped)<0 || stopped.r[0]!=0){out("MUNMAP RESULT FAIL\n");goto done;}
 out("REMOTE MUNMAP OK\n");remote_page=0;
 failed=0;
 done:
 if(attached && stopped_flag){ /* Restore ONLY at verified stop. */
    if(have_regs && sc4(26,13,pid,0,(int)&original)==0)out("REGISTERS RESTORED\n");
    int detach=sc4(26,17,pid,0,0);
    out(detach==0?"PTRACE_DETACH OK\n":"PTRACE_DETACH FAIL; terminating child\n");if(detach!=0)failed=1;
 }
 sleep_ms(30);
 int progressed=workers_progressed(before);
 (void)sc2(37,pid,9); /* SIGKILL fork-owned child only */
 (void)sc4(114,pid,(int)&st,0,0);
 if(progressed)out("WORKERS PROGRESSED=4/4\n");
 else{out("WORKERS PROGRESS NOT CONFIRMED\n");failed=1;}
 out("CHILD CLEANUP DONE\n");
 out(failed?"FAIL: remote dlopen not proven\n":"PASS: isolated child-private mmap + remote dlopen + munmap + worker progress\n");
 terminate(failed?3:0);
}
__attribute__((noreturn)) void _start(void){_run();terminate(99);}
void __aeabi_memcpy(void *dest,const void *src,unsigned n){unsigned char*d=dest;const unsigned char*s=src;while(n--)*d++=*s++;}
void __aeabi_memcpy8(void *dest,const void *src,unsigned n){__aeabi_memcpy(dest,src,n);}
void *memcpy(void *d,const void *s,unsigned n){unsigned char *a=d;const unsigned char*b=s;for(unsigned i=0;i<n;i++)a[i]=b[i];return d;}
void *memset(void*d,int c,unsigned n){unsigned char*a=d;for(unsigned i=0;i<n;i++)a[i]=(unsigned char)c;return d;}
