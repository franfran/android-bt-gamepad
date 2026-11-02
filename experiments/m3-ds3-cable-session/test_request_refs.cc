#include "request_refs.h"
#include <iostream>
#include <stdexcept>
using namespace retrobox;
void Require(bool ok) { if (!ok) throw std::runtime_error("failed"); }
int main() {
  int tests=0;
  auto check=[&](bool ok){Require(ok);++tests;};
  RequestIdentity base{7,0x1000,0x2000,1,0x11};
  RequestRefPool p;
  void* old=p.Begin(base);
  check(old!=nullptr);
  check(p.PendingIdentity(old).has_value());
  check(p.OnCallback(old,base,SecurityEvent::kDelay).forward);
  check(p.OnCallback(old,base,SecurityEvent::kSuccess).forward);
  check(!p.OnCallback(old,base,SecurityEvent::kSuccess).forward);
  check(!p.PendingIdentity(old));
  auto next=base;next.epoch=2;
  void* newer=p.Begin(next);
  check(newer!=old);
  check(!p.OnCallback(old,next,SecurityEvent::kSuccess).forward);
  check(p.OnCallback(newer,next,SecurityEvent::kFailure).forward);
  check(!p.OnCallback(newer,next,SecurityEvent::kSuccess).forward);
  auto tmp=base;tmp.ccb=0x3000;
  void* c=p.Begin(tmp);
  check(c!=nullptr);
  check(p.RetireCcb(tmp.ccb)==1);
  check(!p.OnCallback(c,tmp,SecurityEvent::kSuccess).forward);
  auto other=base;other.ccb=0x4444;other.psm=0x13;
  void* d=p.Begin(other);
  check(p.RetireLcb(base.lcb)==1);
  check(!p.OnCallback(d,other,SecurityEvent::kSuccess).forward);
  auto reused=base;reused.epoch=3;
  void* e=p.Begin(reused);
  check(e && e!=old);
  auto mismatched=reused;mismatched.hci_handle=10;
  check(!p.OnCallback(e,mismatched,SecurityEvent::kSuccess).forward);
  check(!p.OnCallback(e,reused,SecurityEvent::kSuccess).forward);
  auto invalid=base; invalid.psm=0x17;
  check(p.Begin(invalid)==nullptr);
  invalid=base;invalid.hci_handle=0xffff;
  check(p.Begin(invalid)==nullptr);
  invalid=base;invalid.epoch=0;
  check(p.Begin(invalid)==nullptr);
  invalid=base;invalid.ccb=0;
  check(p.Begin(invalid)==nullptr);
  check(!p.OnCallback(nullptr,base,SecurityEvent::kSuccess).forward);
  check(!p.PendingIdentity(nullptr));
  int dummy=0;
  check(!p.OnCallback(&dummy,base,SecurityEvent::kSuccess).forward);
  RequestRefPool many;
  for(size_t i=0;i<RequestRefPool::kCapacity;i++){
    auto id=base;id.epoch=i+1;
    check(many.Begin(id)!=nullptr);
  }
  check(many.Begin(base)==nullptr);
  check(many.RetireCcb(base.ccb)==RequestRefPool::kCapacity);
  check(many.Begin(base)==nullptr); // tombstones never recycled
  std::cout<<tests<<"/"<<tests<<" PASS (opaque request refs, offline)\n";
}
