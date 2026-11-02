#include "java_admission_bridge.h"
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
using namespace retrobox;
static void Check(bool ok) { if (!ok) throw std::runtime_error("admission invariant"); }
int main() {
  std::vector<std::pair<std::string, std::function<void()>>> cases;
  cases.push_back({"cannot offer before service start", [] {
    JavaAdmissionBridge b; Check(!b.Offer(4, 10, NativeEvidence::kVerifiedStandard));
  }});
  cases.push_back({"normal bonded accepted after Java and descriptor", [] {
    JavaAdmissionBridge b; b.ServiceStarted();
    auto t = *b.Offer(4, 10, NativeEvidence::kVerifiedStandard);
    Check(!b.ReleaseUhidCreate(t));
    Check(b.DescriptorValidated(t));
    Check(!b.ReleaseUhidCreate(t));
    Check(b.Reply(t, JavaVerdict::kAcceptStandard, false, true, true));
    Check(b.ReleaseUhidCreate(t)); Check(!b.ReleaseUhidCreate(t));
    Check(b.AllowInput(t, true, true));
  }});
  cases.push_back({"Java reply first still waits for descriptor", [] {
    JavaAdmissionBridge b; b.ServiceStarted();
    auto t = *b.Offer(4, 10, NativeEvidence::kVerifiedStandard);
    Check(b.Reply(t, JavaVerdict::kAcceptStandard, false, true, true));
    Check(!b.ReleaseUhidCreate(t)); Check(b.DescriptorValidated(t));
    Check(b.ReleaseUhidCreate(t));
  }});
  cases.push_back({"unverified cable candidate never creates UHID", [] {
    JavaAdmissionBridge b; b.ServiceStarted();
    auto t = *b.Offer(4, 10, NativeEvidence::kCableCandidateUnverified);
    Check(b.DescriptorValidated(t));
    Check(b.Reply(t, JavaVerdict::kCableReviewOnly, false, false, true));
    Check(!b.ReleaseUhidCreate(t)); Check(!b.AllowInput(t,true,true));
  }});
  cases.push_back({"cable candidate cannot impersonate bonded approval", [] {
    JavaAdmissionBridge b; b.ServiceStarted();
    auto t = *b.Offer(4, 10, NativeEvidence::kCableCandidateUnverified);
    Check(!b.Reply(t, JavaVerdict::kAcceptStandard, false, true, true));
    Check(!b.ReleaseUhidCreate(t));
  }});
  cases.push_back({"quiet mode, unbonded, forbidden policy rejected", [] {
    for(int reason=0; reason<3; ++reason) {
      JavaAdmissionBridge b; b.ServiceStarted();
      auto t = *b.Offer(4, 10, NativeEvidence::kVerifiedStandard);
      Check(!b.Reply(t, JavaVerdict::kAcceptStandard, reason==0,
                     reason!=1, reason!=2));
      Check(!b.ReleaseUhidCreate(t));
    }
  }});
  cases.push_back({"explicit denial cancels", [] {
    JavaAdmissionBridge b; b.ServiceStarted();
    auto t=*b.Offer(4,10,NativeEvidence::kVerifiedStandard);
    Check(b.Reply(t, JavaVerdict::kDeny, false, true, true));
    Check(b.Active()==0); Check(!b.DescriptorValidated(t));
  }});
  cases.push_back({"replies are one-shot", [] {
    JavaAdmissionBridge b; b.ServiceStarted();
    auto t=*b.Offer(4,10,NativeEvidence::kVerifiedStandard);
    Check(b.Reply(t,JavaVerdict::kAcceptStandard,false,true,true));
    Check(!b.Reply(t,JavaVerdict::kDeny,false,true,true));
  }});
  cases.push_back({"reused handle has a different request id", [] {
    JavaAdmissionBridge b; b.ServiceStarted();
    auto a=*b.Offer(4,10,NativeEvidence::kVerifiedStandard);
    auto c=*b.Offer(4,11,NativeEvidence::kVerifiedStandard);
    Check(a.request_id!=c.request_id);
    Check(!b.Reply(a,JavaVerdict::kAcceptStandard,false,true,true));
    Check(b.Reply(c,JavaVerdict::kAcceptStandard,false,true,true));
  }});
  cases.push_back({"same ACL epoch reoffer still invalidates old ticket", [] {
    JavaAdmissionBridge b; b.ServiceStarted();
    auto a=*b.Offer(4,10,NativeEvidence::kVerifiedStandard);
    auto c=*b.Offer(4,10,NativeEvidence::kVerifiedStandard);
    Check(!b.DescriptorValidated(a)); Check(b.DescriptorValidated(c));
  }});
  cases.push_back({"service restart invalidates Java callbacks", [] {
    JavaAdmissionBridge b; b.ServiceStarted();
    auto a=*b.Offer(4,10,NativeEvidence::kVerifiedStandard);
    b.ServiceStopped(); b.ServiceStarted();
    auto c=*b.Offer(4,10,NativeEvidence::kVerifiedStandard);
    Check(a.service_generation!=c.service_generation);
    Check(!b.Reply(a,JavaVerdict::kAcceptStandard,false,true,true));
    Check(b.Reply(c,JavaVerdict::kAcceptStandard,false,true,true));
  }});
  cases.push_back({"two devices remain isolated", [] {
    JavaAdmissionBridge b; b.ServiceStarted();
    auto a=*b.Offer(4,10,NativeEvidence::kVerifiedStandard);
    auto c=*b.Offer(5,20,NativeEvidence::kVerifiedStandard);
    Check(b.DescriptorValidated(a)); Check(b.DescriptorValidated(c));
    Check(b.Reply(c,JavaVerdict::kAcceptStandard,false,true,true));
    Check(!b.ReleaseUhidCreate(a)); Check(b.ReleaseUhidCreate(c));
  }});
  cases.push_back({"disconnected ticket is revoked before reply", [] {
    JavaAdmissionBridge b; b.ServiceStarted();
    auto t=*b.Offer(4,10,NativeEvidence::kVerifiedStandard);
    Check(b.Revoke(t)); Check(!b.Reply(t,JavaVerdict::kAcceptStandard,false,true,true));
  }});
  cases.push_back({"stale revoke cannot cancel new connection", [] {
    JavaAdmissionBridge b; b.ServiceStarted();
    auto a=*b.Offer(4,10,NativeEvidence::kVerifiedStandard);
    auto c=*b.Offer(4,11,NativeEvidence::kVerifiedStandard);
    Check(!b.Revoke(a)); Check(b.Active()==1);
    Check(b.Revoke(c)); Check(b.Active()==0);
  }});
  cases.push_back({"input needs kernel ready and verified report", [] {
    JavaAdmissionBridge b; b.ServiceStarted();
    auto t=*b.Offer(4,10,NativeEvidence::kVerifiedStandard);
    Check(b.DescriptorValidated(t));
    Check(b.Reply(t,JavaVerdict::kAcceptStandard,false,true,true));
    Check(b.ReleaseUhidCreate(t));
    Check(!b.AllowInput(t,false,true)); Check(!b.AllowInput(t,true,false));
    Check(b.AllowInput(t,true,true)); b.ServiceStopped();
    Check(!b.AllowInput(t,true,true));
  }});
  cases.push_back({"invalid handle and zero ACL epoch are refused", [] {
    JavaAdmissionBridge b; b.ServiceStarted();
    Check(!b.Offer(4,0,NativeEvidence::kVerifiedStandard));
    Check(!b.Offer(0xff,10,NativeEvidence::kVerifiedStandard));
  }});
  size_t passed=0;
  for(const auto& test : cases) {
    try { test.second(); ++passed; }
    catch(const std::exception& e) {
      std::cerr << "FAIL " << test.first << ": " << e.what() << '\n'; return 1;
    }
  }
  std::cout << passed << '/' << cases.size() << " PASS (host-only event-bound Java admission)\n";
}
