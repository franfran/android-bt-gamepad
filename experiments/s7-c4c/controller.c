/* RetroBox S7-C4C (C4C-1/2) cross-process ARM32 test controller.
 * STRICTLY TEST TARGET ONLY: independently launched rbxc4c_target.
 * Never attaches to Bluetooth and cannot accept arbitrary PID or path.
 * The first return trap is resolved from target ELF; following calls
 * use an RX target-private trampoline. This bootstrap is NOT a
 * general Bluetooth injector: Bluetooth lacks the target test symbols.
 * SPDX-License-Identifier: MIT
 */
typedef unsigned int u32;
typedef int i32;
#include "target_offsets.h"
#define DIR "/data/local/tmp/retrobox_s7c4c_test/"
#define PIDFILE DIR "target.pid"
#define LIBRARY DIR "libretrobox_c4c_test.so"
#define MISSING DIR "libretrobox_c4c_intentionally_missing.so"
#define MAP_PAGES 4
#define PAGE 4096u
#define PTRACE 26
#define PEEKDATA 2
#define POKEDATA 5
#define ATTACH 16
#define GETREGS 12
#define SETREGS 13
#define CONT 7
#define DETACH 17
#define SIGTRAP 5
#define SIGKILL 9
#define WNOHANG 1
#define WALL 0x40000000
#define WSTOPSIG(s) (((s)>>8)&255)
#define STOPPED(s) (((s)&255)==0x7f)
struct ts {i32 sec,nsec;};
struct regs {u32 r[18];};
static inline int sc1(int n,int a){register int r0 asm("r0")=a,r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r7):"memory","cc");return r0;}
static inline int sc2(int n,int a,int b){register int r0 asm("r0")=a,r1 asm("r1")=b,r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r7):"memory","cc");return r0;}
static inline int sc3(int n,int a,int b,int c){register int r0 asm("r0")=a,r1 asm("r1")=b,r2 asm("r2")=c,r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory","cc");return r0;}
static inline int sc4(int n,int a,int b,int c,int d){register int r0 asm("r0")=a,r1 asm("r1")=b,r2 asm("r2")=c,r3 asm("r3")=d,r7 asm("r7")=n;asm volatile("svc #0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r7):"memory","cc");return r0;}
static void output(const char*s){int len=0;while(s[len])len++;sc3(4,1,(int)s,len);}
static void hex(u32 n){char b[11]="0x00000000";const char *h="0123456789abcdef";for(int i=0;i<8;i++)b[i+2]=h[(n>>(28-4*i))&15];sc3(4,1,(int)b,10);}
static int str_len(const char*s){int n=0;while(s[n])n++;return n;}
static int str_eq(const char*a,const char*b){int i=0;while(a[i]&&b[i]&&a[i]==b[i])i++;return a[i]==b[i];}
static int contains(const char*s,int n,const char*p){int m=str_len(p);for(int i=0;i+m<=n;i++){int j=0;while(j<m&&s[i+j]==p[j])j++;if(j==m)return 1;}return 0;}
static void pidpath(char*buf,int pid,const char*tail){char digits[16];int n=0,k=0;do{digits[n++]=(char)('0'+pid%10);pid/=10;}while(pid>0);const char*q="/proc/";while(*q)buf[k++]=*q++;while(n)buf[k++]=digits[--n];while(*tail)buf[k++]=*tail++;buf[k]=0;}
static int read_text(const char*path,char*buf,int cap){int fd=sc3(5,(int)path,0,0);if(fd<0)return -1;int pos=0,r;while(pos<cap-1&&(r=sc3(3,fd,(int)(buf+pos),cap-pos-1))>0)pos+=r;sc1(6,fd);if(r<0)return -1;buf[pos]=0;return pos;}
static int millis(void){struct ts t;if(sc2(263,1,(int)&t)<0)return -1;return t.sec*1000+t.nsec/1000000;}
static void sleep_ms(int m){struct ts t={m/1000,(m%1000)*1000000};sc2(162,(int)&t,0);}
static int parse_num(const char*s){int n=0,i=0;if(s[0]<'0'||s[0]>'9')return -1;while(s[i]>='0'&&s[i]<='9'){if(n>10000000)return -1;n=n*10+(s[i++]-'0');}return n;}
static int after(const char*s,const char*label){int n=str_len(s),m=str_len(label);for(int i=0;i+m<=n;i++){int j=0;while(j<m&&s[i+j]==label[j])j++;if(j==m){int k=i+m;while(s[k]==' '||s[k]=='\t')k++;return parse_num(s+k);}}return -1;}
static u32 from_hex(const char*s){u32 n=0;int k=0;while(1){int d;char c=s[k++];if(c>='0'&&c<='9')d=c-'0';else if(c>='a'&&c<='f')d=c-'a'+10;else if(c>='A'&&c<='F')d=c-'A'+10;else break;n=(n<<4)|d;}return n;}
/* Avoid trusting PID alone: enforce test-only comm, command line, UID,
 * TracerPid and >=49 threads before any ptrace operations. */
static int validate_target(int pid,int tracer_expected){
 char path[80],comm[256],cmd[512],status[8192];
 pidpath(path,pid,"/comm");int n=read_text(path,comm,sizeof(comm));if(n<0||!str_eq(comm,"rbxc4c_target\n"))return 0;
 pidpath(path,pid,"/cmdline");n=read_text(path,cmd,sizeof(cmd));if(n<0||!contains(cmd,n,"/rbxc4c_target"))return 0;
 pidpath(path,pid,"/status");n=read_text(path,status,sizeof(status));
 if(n<0||after(status,"Uid:")!=0||after(status,"Threads:")<49)return 0;
 if(tracer_expected==0&&after(status,"TracerPid:")!=0)return 0;
 return 1;
}
static char maps_buf[32768];
static int maps_read(int pid){char path[80];pidpath(path,pid,"/maps");return read_text(path,maps_buf,sizeof(maps_buf));}
static u32 target_base(int pid){int n=maps_read(pid);if(n<0)return 0;int i=0;
 while(i<n){int start=i;while(i<n&&maps_buf[i]!='\n')i++;int end=i;
   /* first file mapping has offset zero; path is exact full binary */
   if(contains(maps_buf+start,end-start,DIR "rbxc4c_target")){
     int j=start;while(j<end&&maps_buf[j]!=' ')j++;while(j<end&&maps_buf[j]==' ')j++;
     while(j<end&&maps_buf[j]!=' ')j++;while(j<end&&maps_buf[j]==' ')j++;
     if(j+8<=end&&contains(maps_buf+j,8,"00000000"))return from_hex(maps_buf+start);
   }i++;
 }return 0;
}
static int mapped(int pid,const char*needle){int n=maps_read(pid);return n>0&&contains(maps_buf,n,needle);}
static int address_exec(int pid,u32 addr){int n=maps_read(pid);if(n<0)return 0;int i=0;
 while(i<n){int s=i;while(i<n&&maps_buf[i]!='\n')i++;int e=i;u32 lo=from_hex(maps_buf+s);int j=s;while(j<e&&maps_buf[j]!='-')j++;u32 hi=from_hex(maps_buf+j+1);while(j<e&&maps_buf[j]!=' ')j++;while(j<e&&maps_buf[j]==' ')j++;
 if(lo<=addr&&addr<hi&&j+2<e&&maps_buf[j+2]=='x')return 1;i++;
 }return 0;
}
static int peek(int pid,u32 addr,u32*val){u32 word=0;int rc=sc4(PTRACE,PEEKDATA,pid,(int)addr,(int)&word);if(rc!=0)return 0;*val=word;return 1;}
static int poke(int pid,u32 addr,u32 val){return sc4(PTRACE,POKEDATA,pid,(int)addr,(int)val)==0;}
static int write_string(int pid,u32 addr,const char*s){int len=str_len(s)+1;for(int i=0;i<len;i+=4){u32 value=0,read=0;for(int j=0;j<4;j++){if(i+j<len)value|=((u32)(unsigned char)s[i+j])<<(8*j);}if(!poke(pid,addr+i,value)||!peek(pid,addr+i,&read)||read!=value)return 0;}return 1;}
static int waitstop(int pid,int timeout,int *status){int end=millis()+timeout;while(millis()<end){int r=sc4(114,pid,(int)status,WNOHANG|WALL,0);if(r==pid)return STOPPED(*status)?1:-1;if(r<0)return -2;sleep_ms(10);}return 0;}
static int copyregs(struct regs*d,const struct regs*s){for(int i=0;i<18;i++)d->r[i]=s->r[i];return 1;}
/* Return only after verified SIGTRAP AND PC at expected target trap.
 * NEVER resume a stalled/indeterminate call in this demo. Test-target kill only. */
static int remote_call(int pid,const struct regs*orig,u32 fn,u32 trap,const u32 args[6],int timeout,u32*result){
 struct regs r,stop;int status;copyregs(&r,orig);
 for(int i=0;i<6;i++)r.r[i]=args[i];
 r.r[14]=trap;r.r[15]=fn&~1u;r.r[16]=(r.r[16]&~0x20u)|((fn&1u)?0x20u:0);r.r[17]=0xffffffffu;
 if(sc4(PTRACE,SETREGS,pid,0,(int)&r)<0)return -1;
 if(sc4(PTRACE,CONT,pid,0,0)<0)return -1;
 int w=waitstop(pid,timeout,&status);
 if(w!=1)return -2; /* Indeterminate; do NOT detach and resume */
 if(WSTOPSIG(status)!=SIGTRAP||sc4(PTRACE,GETREGS,pid,0,(int)&stop)<0)return -3;
 if(!(stop.r[15]>=trap&&stop.r[15]<=trap+4))return -4;
 *result=stop.r[0];
 if(sc4(PTRACE,SETREGS,pid,0,(int)orig)<0)return -5;
 if(sc4(PTRACE,GETREGS,pid,0,(int)&stop)<0)return -6;
 for(int i=0;i<18;i++)if(stop.r[i]!=orig->r[i])return -7;
 return 1;
}
/* Remote C string from a returned pointer; ptrace PEEKDATA is word-oriented. */
static int remote_cstring(int pid,u32 addr,char*out,int cap){
 if(!addr||cap<2)return 0;
 u32 aligned=addr&~3u,word=0;int last=-1;
 for(int i=0;i<cap-1;i++){
   u32 a=addr+(u32)i,u=a&~3u;
   if(last!=(int)u){if(!peek(pid,u,&word))return 0;last=(int)u;}
   char c=(char)(word>>(8*(a&3u)));
   out[i]=c;
   if(!c){return i>0;}
   /* Keep log ASCII-safe; no accidental paths/IPs or terminal escapes. */
   if((unsigned char)c<32 || (unsigned char)c>126)out[i]='?';
 }
 out[cap-1]=0;return 0;
}
static int filepid(void){char b[40];int n=read_text(PIDFILE,b,sizeof(b));if(n<1||n>12)return -1;return parse_num(b);}
__attribute__((noreturn)) static void quit(int code){sc1(1,code);for(;;){}}
static int run(void){
 output("RetroBox S7-C4C separately-started ARM32 test-target remote lifecycle\n");
 output("TEST TARGET ONLY: NO BLUETOOTH, NO SYSTEM LIBRARY MODIFICATION\n");
 int pid=filepid();if(pid<1||!validate_target(pid,0)){output("FAIL CLOSED: test target identity/UID/thread check\n");return 2;}
 u32 base=target_base(pid);if(!base){output("FAIL CLOSED: test target PIE base missing\n");return 2;}
 u32 bootstrap=base+OFF_RBXC4C_RETURN_TRAP, mapfn=base+OFF_RBXC4C_MMAP2;
 u32 protfn=base+OFF_RBXC4C_MPROTECT,unmapfn=base+OFF_RBXC4C_MUNMAP;
 u32 loadfn=base+OFF_RBXC4C_LOAD;
 if(!address_exec(pid,bootstrap)||!address_exec(pid,mapfn)||!address_exec(pid,protfn)||!address_exec(pid,unmapfn)||!address_exec(pid,loadfn)){
  output("FAIL CLOSED: target function not executable / invalid PIE address\n");return 2;
 }
 output("TARGET_IDENTITY_CONFIRMED; load_bias=");hex(base);output("\n");
 int attached=0,stopped=0,status=0;u32 scratch=0;int fail=1,phase=0;struct regs orig;
 if(sc4(PTRACE,ATTACH,pid,0,0)<0){output("FAIL: attach\n");return 2;}
 attached=1;
 if(waitstop(pid,1500,&status)!=1){output("FAIL: attach wait\n");goto done;}
 stopped=1;
 if(!validate_target(pid,1)){output("FAIL: target identity changed\n");goto done;}
 if(sc4(PTRACE,GETREGS,pid,0,(int)&orig)<0 || (orig.r[13]&7u)){
  output("FAIL: target stack ABI/regs\n");goto done;
 }
 /* Four private pages: guard | RW data | RX trampoline | guard. */
 u32 args[6]={0,MAP_PAGES*PAGE,0,0x22,0xffffffffu,0};u32 res=0;
 if(remote_call(pid,&orig,mapfn,bootstrap,args,1500,&res)!=1)goto done;
 if(res>=0xfffff001u||(res&(PAGE-1u))){output("FAIL: mmap2\n");goto done;}
 scratch=res;phase=1;
 output("TARGET-PRIVATE MMAP2 OK\n");
 args[0]=scratch+PAGE;args[1]=PAGE*2;args[2]=3;args[3]=args[4]=args[5]=0;
 if(remote_call(pid,&orig,protfn,bootstrap,args,1500,&res)!=1||res!=0)goto done;
 /* Page 2 holds ARM BKPT #0 + BX LR, no Thumb pointer ambiguity. */
 if(!poke(pid,scratch+PAGE*2,0xe1200070u)||!poke(pid,scratch+PAGE*2+4,0xe12fff1eu))goto done;
 u32 check=0;if(!peek(pid,scratch+PAGE*2,&check)||check!=0xe1200070u)goto done;
 args[0]=scratch+PAGE*2;args[1]=PAGE;args[2]=5;
 if(remote_call(pid,&orig,protfn,bootstrap,args,1500,&res)!=1||res!=0)goto done;
 u32 trap=scratch+PAGE*2;
 if(!address_exec(pid,trap)){output("FAIL: RX trap not executable\n");goto done;}
 output("TARGET-OWNED RX RETURN TRAMPOLINE VERIFIED\n");
 const u32 ca=0x52424331u,cb=0x52424332u;
 u32 data=scratch+PAGE;
 if(!poke(pid,data,ca)||!poke(pid,data+4,cb))goto done;
 if(!write_string(pid,data+64,MISSING)||!write_string(pid,data+256,LIBRARY))goto done;
 /* Negative library load test; proves returning NULL safely. */
 args[0]=data+64;args[1]=args[2]=args[3]=args[4]=args[5]=0;
 phase=2;
 int rc=remote_call(pid,&orig,loadfn,trap,args,2500,&res);
 if(rc!=1){output("QUARANTINE: remote dlopen did not return cleanly; NO RETRY\n");goto done;}
 if(res!=0){output("FAIL: missing library returned non-null\n");goto done;}
 output("EXPECTED MISSING LIBRARY: DLOPEN NULL\n");
 /* This proves the negative result included a retrievable linker error. */
 args[0]=args[1]=args[2]=args[3]=args[4]=args[5]=0;
 u32 errorfn=base+OFF_RBXC4C_ERROR;
 rc=remote_call(pid,&orig,errorfn,trap,args,1500,&res);
 char error[192];
 if(rc!=1||!remote_cstring(pid,res,error,sizeof(error))){output("FAIL: missing dlerror detail\n");goto done;}
 output("REMOTE DLERROR CAPTURED (nonempty)\n");
 args[0]=data+256;
 rc=remote_call(pid,&orig,loadfn,trap,args,2500,&res);
 if(rc!=1){output("QUARANTINE: remote dlopen did not return cleanly; NO RETRY\n");goto done;}
 if(!res){output("FAIL: test add-on could not load (namespace / linker)\n");goto done;}
 if(!mapped(pid,"libretrobox_c4c_test.so")){output("FAIL: test add-on mapping missing\n");goto done;}
 u32 v1=0,v2=0;if(!peek(pid,data,&v1)||!peek(pid,data+4,&v2)||v1!=ca||v2!=cb){output("FAIL: scratch canary\n");goto done;}
 output("TEST MODULE LOADED IN INDEPENDENT TARGET; CANARIES VERIFIED\n");
 u32 tick_before=0,tick_after=0;
 if(!peek(pid,base+OFF_RBXC4C_TICKS,&tick_before))goto done;
 sleep_ms(150);
 if(!peek(pid,base+OFF_RBXC4C_TICKS,&tick_after)||tick_after<=tick_before){output("FAIL: worker progression\n");goto done;}
 output("BACKGROUND WORKERS PROGRESSED WHILE LEADER TRACED\n");
 /* Return to bootstrap trap because unmapping trampoline from within itself
  * would race the instruction stream. */
 args[0]=scratch;args[1]=MAP_PAGES*PAGE;args[2]=args[3]=args[4]=args[5]=0;
 rc=remote_call(pid,&orig,unmapfn,bootstrap,args,1500,&res);
 if(rc!=1||res!=0){output("FAIL: private scratch unmap\n");goto done;}
 scratch=0;
 output("REMOTE MUNMAP COMPLETED; RETURNED VIA TARGET-IMAGE BOOTSTRAP\n");
 if(sc4(PTRACE,DETACH,pid,0,0)<0){output("FAIL: detach\n");goto done;}
 stopped=0;attached=0;
 output("PASS: non-fork independent ARM32 target call, RX trampoline, dlopen negative/positive, cleanup\n");
 fail=0;
 done:
 if(fail){
   output(phase>=2?"STATE=QUARANTINE; SAFE_TO_RETRY=false\n":"STATE=PRECALL_FAILURE; SAFE_TO_RETRY=false\n");
   /* Only our independently launched *test* process can be terminated.
    * Never leave a traced target that may be midway through linker call.
    * The wrapper also performs a scoped cleanup if this controller exits. */
   if(attached){sc2(37,pid,SIGKILL);output("SCOPED TEST TARGET SIGKILL REQUESTED\n");}
 }
 return fail?3:0;
}
__attribute__((noreturn)) void _start(void){int r=run();quit(r);}