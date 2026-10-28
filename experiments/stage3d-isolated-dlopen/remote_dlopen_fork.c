/* RetroBox D2b-2c: isolated remote dlopen using fork-owned child ONLY.
 * Android ARM32, no libc dependency, no external PID input.
 * This program never accesses com.android.bluetooth.
 * SPDX-License-Identifier: MIT
 */
typedef unsigned int u32;
extern void *dlopen(const char *, int);
static const char path[]="/data/local/tmp/retrobox_stage3d_d2b2c/libretrobox_ds3_addon.so";
static inline int sc1(int n,int a){register int r0 __asm__("r0")=a; register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r7):"memory");return r0;}
static inline int sc2(int n,int a,int b){register int r0 __asm__("r0")=a;register int r1 __asm__("r1")=b;register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r7):"memory");return r0;}
static inline int sc3(int n,int a,int b,int c){register int r0 __asm__("r0")=a;register int r1 __asm__("r1")=b;register int r2 __asm__("r2")=c;register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory");return r0;}
static inline int sc4(int n,int a,int b,int c,int d){register int r0 __asm__("r0")=a;register int r1 __asm__("r1")=b;register int r2 __asm__("r2")=c;register int r3 __asm__("r3")=d;register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r7):"memory");return r0;}
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
__attribute__((naked,noinline,used)) static void return_trap(void){__asm__ volatile("bkpt #0");}
__attribute__((noreturn)) static void terminate(int code){(void)sc1(1,code);for(;;){}}
struct regs {u32 r[18];}; /* ARM user_regs: r0..r15, CPSR, ORIG_R0 */
static void _run(void){
 out("RetroBox D2b-2c isolated remote dlopen (forked child only)\n");
 out("No Bluetooth process, no arbitrary PID, no authentication modifications.\n");
 int pid=sc1(2,0);
 if(pid==0){for(;;)(void)sc1(29,0);} /* child pause() forever until parent cleanup */
 if(pid<0){out("FORK FAILED\n");terminate(2);}
 out("CHILD CREATED pid=");hex((u32)pid);newline();
 int attached=0,rc=0,st=0,failed=1;
 rc=sc4(26,16,pid,0,0);
 if(rc<0){out("PTRACE_ATTACH FAIL errno=");hex((u32)-rc);newline();goto done;}
 attached=1;
 rc=sc4(114,pid,(int)&st,0,0);
 if(rc<0 || (st&255)!=127){out("WAIT ATTACH STOP FAIL\n");goto done;}
 out("PTRACE_ATTACH OK\n");
 struct regs original, modified, stopped;
 rc=sc4(26,12,pid,0,(int)&original);
 if(rc<0){out("GETREGS FAIL errno=");hex((u32)-rc);newline();goto done;}
 out("PTRACE_GETREGS OK\n");
 for(int i=0;i<18;i++)modified.r[i]=original.r[i];
 u32 fn=(u32)dlopen;u32 trap=(u32)return_trap;
 out("REMOTE dlopen address=");hex(fn);newline();
 out("RETURN trap address=");hex(trap);newline();
 modified.r[0]=(u32)path;
 modified.r[1]=2; /* RTLD_NOW */
 modified.r[15]=fn & ~1u;
 modified.r[14]=trap;
 modified.r[16]=(modified.r[16]&~0x20u)|((fn&1u)?0x20u:0);
 modified.r[17]=0xffffffffu; /* avoid restarting interrupted pause syscall */
 rc=sc4(26,13,pid,0,(int)&modified);
 if(rc<0){out("SETREGS FAIL errno=");hex((u32)-rc);newline();goto done;}
 out("REMOTE CALL ARMED\n");
 rc=sc4(26,7,pid,0,0); /* PTRACE_CONT */
 if(rc<0){out("PTRACE_CONT FAIL\n");goto done;}
 rc=sc4(114,pid,(int)&st,0,0);
 if(rc<0 || (st&255)!=127){out("WAIT REMOTE CALL FAIL\n");goto done;}
 int signo=(st>>8)&255;
 out("CHILD STOP signal=");hex((u32)signo);newline();
 rc=sc4(26,12,pid,0,(int)&stopped);
 if(rc<0){out("REMOTE GETREGS FAIL\n");goto done;}
 out("REMOTE RETURN r0=");hex(stopped.r[0]);newline();
 if(signo!=5){out("REMOTE CALL DID NOT REACH TRAP (expected SIGTRAP=5)\n");goto done;}
 if(!stopped.r[0]){out("DLOPEN RETURNED NULL\n");goto done;}
 out("REMOTE DLOPEN NONNULL\n");
 rc=maps_contains(pid);
 if(rc!=1){out(rc==0?"ADDON MAPPING NOT FOUND\n":"COULD NOT READ CHILD MAPS\n");goto done;}
 out("ADDON MAPPED IN CHILD: YES\n");
 failed=0;
 done:
 if(attached){ /* Restore registers while the child is stopped, then safely terminate it. */
    if(sc4(26,13,pid,0,(int)&original)==0)out("REGISTERS RESTORED\n");
    int detach=sc4(26,17,pid,0,0);
    out(detach==0?"PTRACE_DETACH OK\n":"PTRACE_DETACH FAIL; terminating child\n");
 }
 (void)sc2(37,pid,9); /* SIGKILL fork-owned child only */
 (void)sc4(114,pid,(int)&st,0,0);
 out("CHILD CLEANUP DONE\n");
 out(failed?"FAIL: remote dlopen not proven\n":"PASS: isolated remote dlopen and maps verification\n");
 terminate(failed?3:0);
}
__attribute__((noreturn)) void _start(void){_run();terminate(99);}
