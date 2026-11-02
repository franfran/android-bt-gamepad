#include "provisional_uhid_gate.h"
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>
using namespace retrobox;
static void Must(bool ok) { if (!ok) throw std::runtime_error("provisional gate assertion"); }
int main() {
  std::vector<std::pair<std::string,std::function<void()>>> cases;
  const StandardEvidence good{true,true,true,true,true};
  const StandardEvidence noauth{false,true,true,true,true};
  auto add=[&](std::string name,std::function<void()> fn){cases.emplace_back(std::move(name),std::move(fn));};
  add("unknown fd fails closed including early events", []{
    ProvisionalUhidGate g;int writes=0;
    Must(g.WithWrite(7,UhidOp::kCreate,[&]{++writes;return 0;})==-EACCES);
    Must(g.WithWrite(7,UhidOp::kInput,[&]{++writes;return 0;})==-EACCES);
    Must(writes==0);
    Must(g.WithWrite(7,UhidOp::kDestroy,[&]{++writes;return 0;})==0);
  });
  add("newly opened fd is provisional before peer classification", []{
    ProvisionalUhidGate g;auto a=g.Open(7,4);Must(a.has_value());
    Must(g.WithWrite(7,UhidOp::kCreate,[]{return 1;})==-EACCES);
    Must(g.WithWrite(7,UhidOp::kInput,[]{return 1;})==-EACCES);
  });
  add("unverified cable candidate never promotes", [good]{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);
    Must(g.MarkCandidate(a));Must(!g.PermitStandard(a,good));
    Must(g.WithWrite(7,UhidOp::kCreate,[]{return 1;})==-EACCES);
  });
  add("normal authenticated bonded HID may be released", [good]{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);
    Must(g.PermitStandard(a,good));int writes=0;
    Must(g.WithWrite(7,UhidOp::kCreate,[&]{++writes;return 0;})==0);
    Must(g.WithWrite(7,UhidOp::kInput,[&]{++writes;return 0;})==0);
    Must(writes==2);
  });
  add("native authentication absence denies", [noauth]{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);Must(!g.PermitStandard(a,noauth));
  });
  add("ACL mismatch denies", [good]{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);auto e=good;e.acl_session_matches=false;Must(!g.PermitStandard(a,e));
  });
  add("unbonded Java denies", [good]{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);auto e=good;e.java_bonded=false;Must(!g.PermitStandard(a,e));
  });
  add("Java policy denies", [good]{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);auto e=good;e.java_policy_allowed=false;Must(!g.PermitStandard(a,e));
  });
  add("descriptor not validated denies", [good]{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);auto e=good;e.descriptor_validated=false;Must(!g.PermitStandard(a,e));
  });
  add("failed registration must close and abort", []{
    ProvisionalUhidGate g;Must(!g.Open(-1,4));Must(!g.Open(7,0xff));
    auto a=g.Open(7,4);Must(a.has_value());Must(!g.Open(7,5));Must(!g.Open(8,4));
    Must(g.WithWrite(8,UhidOp::kInput,[]{return 0;})==-EACCES);
  });
  add("candidate quarantine cannot grant", [good]{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);Must(g.MarkCandidate(a));Must(g.Quarantine(a));
    Must(!g.PermitStandard(a,good));Must(!g.MarkCandidate(a));
    Must(g.WithWrite(7,UhidOp::kInput,[]{return 0;})==-EACCES);
  });
  add("standard disconnect quarantines before close", [good]{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);Must(g.PermitStandard(a,good));
    Must(g.Quarantine(a));Must(g.WithWrite(7,UhidOp::kInput,[]{return 0;})==-EACCES);
  });
  add("close failure keeps tombstone", []{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);Must(!g.Close(a,[](int){return false;}));
    Must(g.Count()==1);Must(!g.Open(7,4));
    Must(g.WithWrite(7,UhidOp::kCreate,[]{return 0;})==-EACCES);
  });
  add("verified close permits fd reuse with fresh token", []{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);Must(g.Close(a,[](int){return true;}));
    auto b=g.Open(7,4);Must(b&&b->open_generation!=a.open_generation);
    Must(!g.Close(a,[](int){std::terminate();return true;}));
    Must(g.WithWrite(7,UhidOp::kInput,[]{return 0;})==-EACCES);
  });
  add("stale close cannot affect another candidate", []{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);auto b=*g.Open(8,5);
    Must(!g.Close({7,4,a.open_generation+1},[](int){return true;}));
    Must(g.Count()==2);Must(g.MarkCandidate(b));
    Must(g.WithWrite(8,UhidOp::kCreate,[]{return 0;})==-EACCES);
  });
  add("full registry fails closed", []{
    ProvisionalUhidGate g;for(int i=0;i<8;++i)Must(g.Open(100+i,static_cast<uint8_t>(i)).has_value());
    Must(!g.Open(300,40));
    Must(g.WithWrite(300,UhidOp::kInput,[]{return 0;})==-EACCES);
    Must(g.Count()==8);
  });
  add("close frees capacity and maintains monotonic generation", []{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);Must(g.Close(a,[](int){return true;}));
    auto b=g.Open(8,5);Must(b&&b->open_generation>a.open_generation);
  });
  add("no write after quarantine before close", [good]{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);Must(g.PermitStandard(a,good));
    int writes=0;Must(g.WithWrite(7,UhidOp::kInput,[&]{++writes;return 0;})==0);
    Must(g.Quarantine(a));Must(g.WithWrite(7,UhidOp::kInput,[&]{++writes;return 0;})==-EACCES);
    Must(writes==1);
  });
  add("write and close serialized through same lock", [good]{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);Must(g.PermitStandard(a,good));
    int writes=0;g.WithWrite(7,UhidOp::kInput,[&]{writes++;return 0;});
    Must(g.Close(a,[](int){return true;}));
    Must(g.WithWrite(7,UhidOp::kInput,[&]{writes++;return 0;})==-EACCES);
    Must(writes==1);
  });
  add("normal session cannot reopen as candidate until closed", [good]{
    ProvisionalUhidGate g;auto a=*g.Open(7,4);Must(g.PermitStandard(a,good));
    Must(!g.Open(7,4));Must(!g.MarkCandidate(a));
  });
  size_t passed=0;
  for(const auto& c:cases){try{c.second();passed++;}catch(const std::exception& e){std::cerr<<"FAIL "<<c.first<<": "<<e.what()<<"\n";return 1;}}
  std::cout<<passed<<"/"<<cases.size()<<" PASS (provisional UHID session lifecycle host)\n";
}
