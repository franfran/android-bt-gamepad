/* RetroBox DS3 Stage 1: conservative AF_BLUETOOTH L2CAP bind probe.
 * Creates L2CAP socket, binds only temporary non-DS3 PSM 0x1001,
 * closes immediately. Does not listen/connect, modify pairing or write HCI.
 * Direct Linux ARM32 EABI syscalls; no libc/NDK. MIT license.
 */
typedef unsigned short u16;
typedef unsigned char u8;
struct sockaddr_l2_min {
  u16 l2_family; u16 l2_psm; u8 l2_bdaddr[6]; u16 l2_cid; u8 l2_bdaddr_type;
};
static inline int sc1(int n,int a){register int r0 __asm__("r0")=a;register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r7):"memory");return r0;}
static inline int sc3(int n,int a,int b,int c){register int r0 __asm__("r0")=a;register int r1 __asm__("r1")=b;register int r2 __asm__("r2")=c;register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory");return r0;}
static int slen(const char *s){int n=0;while(s[n])n++;return n;}
static void out(const char*s){sc3(4,1,(int)s,slen(s));}
static void num(int v){char b[16];int i=15;b[i]=0;unsigned n=v<0?(unsigned)(-(v+1))+1u:(unsigned)v;do{b[--i]='0'+n%10;n/=10;}while(n);if(v<0)b[--i]='-';out(b+i);}
__attribute__((noreturn)) void _start(void){
 out("RetroBox DS3 Bluetooth Stage 1 ARM32 static\n");
 out("Test: bind L2CAP SEQPACKET on temporary PSM 0x1001 (no listen/connect)\n");
 int fd=sc3(281,31,5,0);
 if(fd<0){out("SOCKET FAIL errno=");num(-fd);out("\n");sc1(1,1);}
 struct sockaddr_l2_min addr={0};addr.l2_family=31;addr.l2_psm=0x1001;
 int rv=sc3(282,fd,(int)&addr,(int)sizeof(addr));
 if(rv<0){out("BIND FAIL errno=");num(-rv);out("\n");}
 else out("BIND SUCCESS (temporary PSM only; no DS3 connection)\n");
 sc1(6,fd);out("Socket closed. No Bluetooth configuration changed.\n");sc1(1,rv<0?2:0);for(;;){}
}
