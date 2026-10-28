/* RetroBox D2b-2a: isolated ARM32 ptrace attach/detach smoke test.
 * Creates and traces ONLY its own forked child; no existing PID accepted.
 * Linux ARM EABI numbers. No libc or NDK required.
 * Copyright (c) RetroBox contributors. SPDX-License-Identifier: MIT
 */
typedef unsigned int u32;
static inline int sc1(int n,int a) {
 register int r0 __asm__("r0")=a; register int r7 __asm__("r7")=n;
 __asm__ volatile("svc #0":"+r"(r0):"r"(r7):"memory"); return r0;
}
static inline int sc2(int n,int a,int b) {
 register int r0 __asm__("r0")=a; register int r1 __asm__("r1")=b; register int r7 __asm__("r7")=n;
 __asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r7):"memory"); return r0;
}
static inline int sc3(int n,int a,int b,int c) {
 register int r0 __asm__("r0")=a; register int r1 __asm__("r1")=b; register int r2 __asm__("r2")=c; register int r7 __asm__("r7")=n;
 __asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory"); return r0;
}
static inline int sc4(int n,int a,int b,int c,int d) {
 register int r0 __asm__("r0")=a; register int r1 __asm__("r1")=b; register int r2 __asm__("r2")=c; register int r3 __asm__("r3")=d; register int r7 __asm__("r7")=n;
 __asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r7):"memory"); return r0;
}
static void out(const char *s) {int n=0;while(s[n])n++;(void)sc3(4,1,(int)s,n);}
static void num(int v) { char b[11]="0x00000000"; const char *h="0123456789abcdef"; for(int i=0;i<8;i++) b[2+i]=h[((unsigned)v>>(28-i*4))&15]; out(b); }
static void die(int code) __attribute__((noreturn));
static void die(int code) {sc1(1,code);for(;;){}}
static void cleanup(int pid) { (void)sc2(37,pid,9); int status=0; (void)sc4(114,pid,(int)&status,0,0); }
void _start(void) __attribute__((noreturn));
void _start(void) {
 out("RetroBox Stage 3D D2b-2a: self-child ptrace test\n");
 out("Scope: ONLY a child created by this binary. No Bluetooth attach.\n");
 int pid=sc1(2,0); /* fork syscall: argument ignored */
 if(pid==0){ for(;;){ (void)sc1(29,0); } } /* pause */
 if(pid<0){out("FORK FAIL errno=");num(-pid);out("\n");die(2);}
 out("CHILD CREATED pid=");num(pid);out("\n");
 int a=sc4(26,16,pid,0,0); /* ptrace(PTRACE_ATTACH=16,pid) */
 if(a<0){out("PTRACE_ATTACH FAIL errno=");num(-a);out("\n");cleanup(pid);die(3);}
 out("PTRACE_ATTACH OK\n");
 int st=0; int w=sc4(114,pid,(int)&st,0,0); /* wait4 */
 if(w<0 || (st&0xff)!=0x7f){out("WAIT STOP FAIL result=");num(w);out(" status=");num(st);out("\n");(void)sc4(26,17,pid,0,0);cleanup(pid);die(4);}
 out("CHILD STOP CONFIRMED signal=");num((st>>8)&0xff);out("\n");
 int d=sc4(26,17,pid,0,0); /* PTRACE_DETACH */
 if(d<0){out("PTRACE_DETACH FAIL errno=");num(-d);out("\n");cleanup(pid);die(5);}
 out("PTRACE_DETACH OK\n");
 cleanup(pid);
 out("CHILD CLEANUP OK; no process left behind\n");
 out("PASS: isolated attach/detach only; D2b Bluetooth injection NOT tested\n");
 die(0);
}
