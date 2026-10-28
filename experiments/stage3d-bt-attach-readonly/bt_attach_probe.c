/* RetroBox D2b-2d-A. Passive ptrace seize/interrupt/detach.
 * ARM32 Linux syscalls, no libc. Exact process comm gate.
 * Does NOT change registers, memory, auth, or inject code.
 * SPDX-License-Identifier: MIT
 */
typedef unsigned int u32;
static inline int sc1(int n,int a){register int r0 __asm__("r0")=a;register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r7):"memory");return r0;}
static inline int sc2(int n,int a,int b){register int r0 __asm__("r0")=a;register int r1 __asm__("r1")=b;register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r7):"memory");return r0;}
static inline int sc3(int n,int a,int b,int c){register int r0 __asm__("r0")=a;register int r1 __asm__("r1")=b;register int r2 __asm__("r2")=c;register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory");return r0;}
static inline int sc4(int n,int a,int b,int c,int d){register int r0 __asm__("r0")=a;register int r1 __asm__("r1")=b;register int r2 __asm__("r2")=c;register int r3 __asm__("r3")=d;register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r7):"memory");return r0;}
static void out(const char*s){int i=0;while(s[i])i++;(void)sc3(4,1,(int)s,i);}
static void hex(u32 n){char b[]="0x00000000";const char h[]="0123456789abcdef";for(int i=0;i<8;i++)b[i+2]=h[(n>>(28-4*i))&15];out(b);}
static void done(int c)__attribute__((noreturn));static void done(int c){sc1(1,c);for(;;){}}
static int parse(const char*s){int x=0,n=0;for(;*s;s++){if(*s<'0'||*s>'9'||++n>8)return -1;x=x*10+(*s-'0');}return n?x:-1;}
static int proc_comm(int pid){char p[]="/proc/00000000/comm";int i=6,v=pid;char t[9];int n=0;do{t[n++]=(char)('0'+v%10);v/=10;}while(v&&n<8);while(n)p[i++]=t[--n];p[i++]='/';p[i++]='c';p[i++]='o';p[i++]='m';p[i++]='m';p[i]=0;
 int fd=sc3(5,(int)p,0,0);if(fd<0)return fd;char b[40];int r=sc3(3,fd,(int)b,39);sc1(6,fd);if(r<0)return r;b[r]=0;const char *expected="droid.bluetooth";int j=0;while(expected[j]&&j<r&&b[j]==expected[j])j++;return expected[j]==0&&(b[j]=='\n'||b[j]==0)?1:0;}
/* _start receives argc/argv on stack; avoid libc startup. */
static void run(int argc,char **argv) __attribute__((noreturn,used,noinline));
static void run(int argc,char **argv){
 out("RetroBox D2b-2d-A: bluetooth leader thread SEIZE/INTERRUPT/DETACH\n");
 out("No remote calls, register changes, memory writes, or library loads.\n");
 if(argc!=2){out("FAIL usage: bt_attach_probe <pid>\n");done(2);}int pid=parse(argv[1]);if(pid<=1){out("FAIL invalid PID\n");done(2);}
 int match=proc_comm(pid);if(match!=1){out("FAIL process-name gate (expected droid.bluetooth), code=");hex((u32)match);out("\n");done(3);}
 out("TARGET COMM VERIFIED PID=");hex((u32)pid);out("\n");
 int rc=sc4(26,0x4206,pid,0,0);if(rc<0){out("PTRACE_SEIZE FAIL errno=");hex((u32)-rc);out("\n");done(4);}out("PTRACE_SEIZE OK (non-stopping)\n");
 rc=sc4(26,0x4207,pid,0,0);if(rc<0){out("PTRACE_INTERRUPT FAIL errno=");hex((u32)-rc);out("\n");goto release;}
 int status=0;rc=sc4(114,pid,(int)&status,0,0);if(rc!=pid){out("WAIT4 FAIL rc=");hex((u32)rc);out("\n");goto release;}
 out("TRACE STOP status=");hex((u32)status);out("\n");
 if((status&0xff)!=0x7f){out("FAIL unexpected wait status\n");goto release;}
 out("PTRACE_INTERRUPT STOP CONFIRMED\n");
 rc=sc4(26,17,pid,0,0);if(rc<0){out("PTRACE_DETACH FAIL errno=");hex((u32)-rc);out("\n");done(6);}
 out("PTRACE_DETACH OK\nPASS: brief controlled Bluetooth leader thread attach/detach (NO injection)\n");done(0);
 release:
 rc=sc4(26,17,pid,0,0);out(rc==0?"PTRACE_DETACH OK after error\n":"WARNING: detach failed; tracer exit will release ptrace relationship\n");done(5);
}
__attribute__((naked,noreturn)) void _start(void){__asm__ volatile("mov r0, sp\n ldr r1, [r0]\n add r2, r0, #4\n mov r0, r1\n mov r1, r2\n b run\n");}
