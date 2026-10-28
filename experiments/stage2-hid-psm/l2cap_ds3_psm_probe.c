/* RetroBox DS3 Stage 2: non-listening DS3 HID PSM bind probe.
 * ARM32 Linux static syscalls, no libc. Test PSMs 0x11 and 0x13 briefly.
 * No listen/connect/send/HCI commands/device configuration changes.
 * SPDX-License-Identifier: MIT
 */
typedef unsigned short u16;
typedef unsigned char u8;
struct sockaddr_l2_min { u16 family, psm; u8 addr[6]; u16 cid; u8 type; };
static inline int sc1(int n,int a){register int r0 __asm__("r0")=a;register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r7):"memory");return r0;}
static inline int sc3(int n,int a,int b,int c){register int r0 __asm__("r0")=a;register int r1 __asm__("r1")=b;register int r2 __asm__("r2")=c;register int r7 __asm__("r7")=n;__asm__ volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory");return r0;}
static int slen(const char*s){int n=0;while(s[n])n++;return n;}
static void out(const char*s){sc3(4,1,(int)s,slen(s));}
static void num(int v){
  char b[12];int i=0;unsigned n=(unsigned)(v<0?-v:v);
  if(v<0)b[i++]='-';
  unsigned places[5]={10000,1000,100,10,1};int leading=1;
  for(int k=0;k<5;k++){
    unsigned d=0;while(n>=places[k]){n-=places[k];d++;}
    if(d || !leading || k==4){b[i++]=(char)('0'+d);leading=0;}
  }
  b[i]=0;out(b);
}
static int probe(const char *name, u16 psm){
  out(name);out(": ");
  int fd=sc3(281,31,5,0); /* AF_BLUETOOTH SOCK_SEQPACKET BTPROTO_L2CAP */
  if(fd<0){out("SOCKET FAILED errno=");num(-fd);out("\n");return 1;}
  struct sockaddr_l2_min a={0};a.family=31;a.psm=psm;
  int rc=sc3(282,fd,(int)&a,sizeof(a)); /* bind */
  if(rc<0){out("BIND FAILED errno=");num(-rc);out("\n");}
  else out("BIND OK (no listen; closed immediately)\n");
  sc1(6,fd);return rc<0;
}
__attribute__((noreturn)) void _start(void){
 out("RetroBox DS3 Stage 2 - HID PSM bind-only probe\n");
 out("No listen/connect; no HCI or pairing changes.\n");
 int failures=probe("HID Control 0x11",0x11)+probe("HID Interrupt 0x13",0x13);
 out("Sockets closed.\n");sc1(1,failures?2:0);for(;;){}
}
