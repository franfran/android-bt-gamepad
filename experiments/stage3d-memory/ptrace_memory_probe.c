/* RetroBox D2b-2b prerequisite: isolated ptrace remote memory R/W.
 * Operates ONLY on its own forked child. Restores data before detach.
 * No arbitrary PID, no code execution, no dlopen, no Bluetooth operation.
 * SPDX-License-Identifier: MIT
 */
typedef unsigned int u32;
static volatile u32 child_marker = 0x52425831u;
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
static void out(const char *s){int n=0;while(s[n])n++;(void)sc3(4,1,(int)s,n);}
static void num(u32 v){char b[11]="0x00000000"; const char *h="0123456789abcdef";for(int i=0;i<8;i++)b[2+i]=h[(v>>(28-i*4))&15];out(b);}
static void die(int code) __attribute__((noreturn));
static void die(int code){(void)sc1(1,code);for(;;){}}
static void cleanup(int pid){(void)sc2(37,pid,9);int st=0;(void)sc4(114,pid,(int)&st,0,0);}
void _start(void) __attribute__((noreturn));
void _start(void){
 out("RetroBox Stage 3D D2b-2b prerequisite: isolated memory probe\n");
 out("Only fork-owned child; no Bluetooth attach, code injection or dlopen.\n");
 int pid=sc1(2,0);
 if(pid==0){for(;;)(void)sc1(29,0);}
 if(pid<0){out("FORK FAIL errno=");num((u32)-pid);out("\n");die(2);}
 out("CHILD CREATED pid=");num((u32)pid);out("\n");
 int attached=0, result=3;
 int rc=sc4(26,16,pid,0,0); /* PTRACE_ATTACH */
 if(rc<0){out("ATTACH FAIL errno=");num((u32)-rc);out("\n");goto done;}
 attached=1;
 int st=0; rc=sc4(114,pid,(int)&st,0,0);
 if(rc<0 || (st&0xff)!=0x7f){out("WAIT STOP FAIL\n");goto done;}
 out("PTRACE_ATTACH/WAIT OK\n");
 u32 addr=(u32)&child_marker;
 /* Raw Linux ptrace PEEKDATA writes into the fourth-argument pointer. */
 u32 value=0;
 rc=sc4(26,2,pid,(int)addr,(int)&value);
 if(rc<0){out("PEEKDATA FAIL errno=");num((u32)-rc);out("\n");goto done;}
 if(value!=0x52425831u){out("PEEKDATA UNEXPECTED value=");num(value);out("\n");goto done;}
 out("REMOTE PEEKDATA OK marker=");num((u32)value);out("\n");
 rc=sc4(26,5,pid,(int)addr,(int)0x52425832u); /* POKEDATA */
 if(rc<0){out("POKEDATA FAIL errno=");num((u32)-rc);out("\n");goto done;}
 out("REMOTE POKEDATA OK\n");
 u32 updated=0; rc=sc4(26,2,pid,(int)addr,(int)&updated);
 if(rc<0 || updated!=0x52425832u){out("VERIFY FAIL value=");num((u32)updated);out("\n");goto restore;}
 out("REMOTE VERIFY OK marker=");num((u32)updated);out("\n");
 result=0;
 restore:
 rc=sc4(26,5,pid,(int)addr,(int)0x52425831u);
 if(rc<0){out("RESTORE FAIL\n");result=4;}
 else {u32 v=0; int r=sc4(26,2,pid,(int)addr,(int)&v);if(r<0 || v!=0x52425831u){out("RESTORE VERIFY FAIL\n");result=4;}else out("RESTORE VERIFIED\n");}
 done:
 if(attached){rc=sc4(26,17,pid,0,0);out(rc==0?"PTRACE_DETACH OK\n":"PTRACE_DETACH FAILED (child will be killed)\n"); if(rc<0)result=5;}
 cleanup(pid);
 out("CHILD CLEANUP OK\n");
 if(result==0)out("PASS: remote read/write/restore on forked child only\n");
 else out("FAIL: remote memory preflight; no Bluetooth modifications\n");
 die(result);
}
