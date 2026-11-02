#include "usb_enrollment.h"
#include <iostream>
#include <stdexcept>
using namespace retrobox;
void Test(bool ok, int& n) { if (!ok) throw std::runtime_error("failed assertion"); ++n; }
int main() {
  int n = 0;
  BdAddr ds3{{0x13, 0x24, 0x35, 0x46, 0x57, 0x68}};
  BdAddr host{{0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0x01}};
  BdAddr previous{{0xa1, 0xb2, 0xc3, 0xd4, 0xe5, 0xf6}};
  uint8_t f2[18] = {0xf2};
  for(size_t i=0;i<6;++i) f2[4+i]=ds3[5-i];
  auto prev = BuildDs3F5Write(previous);
  auto target = BuildDs3F5Write(host);
  Test(ParseDs3F2(f2,18) == std::optional<BdAddr>(ds3), n);
  Test(ParseDs3F5(prev.data(),prev.size()) == std::optional<BdAddr>(previous), n);
  Test(!ParseDs3F2(nullptr,18), n);
  Test(!ParseDs3F2(f2,17), n);
  Test(!ParseDs3F5(prev.data(),7), n);
  prev[0]=0; Test(!ParseDs3F5(prev.data(),8), n);prev[0]=0xf5;
  UsbEnrollmentTransaction t;
  Test(!t.Begin(false,0x054c,0x0268,f2,18,prev.data(),8,host),n);
  Test(!t.Begin(true,0x054c,0x0267,f2,18,prev.data(),8,host),n);
  Test(t.Begin(true,0x054c,0x0268,f2,18,prev.data(),8,host),n);
  Test(t.State()==EnrollmentState::kAwaitOwner,n);
  Test(!t.RequestedWrite(),n);
  Test(t.CheckRadioAddress(ds3)==RadioClaim::kNoCandidate,n);
  Test(t.OwnerDecision(true),n);
  Test(t.RequestedWrite()==std::optional<std::array<uint8_t,8>>(target),n);
  Test(!t.Readback(target.data(),8),n); // owner approved but write not verified
  Test(t.WriteResult(true),n);
  Test(!t.WriteResult(true),n);
  Test(t.Readback(target.data(),8),n);
  Test(t.State()==EnrollmentState::kCommitted,n);
  Test(t.CheckRadioAddress(ds3)==RadioClaim::kAddressCandidateNotAuthenticated,n);
  Test(t.CheckRadioAddress(previous)==RadioClaim::kNoCandidate,n);
  t.UsbDetached();
  Test(t.State()==EnrollmentState::kCommitted,n);
  t.AdapterChanged(previous);
  Test(t.State()==EnrollmentState::kCancelled,n);
  Test(t.CheckRadioAddress(ds3)==RadioClaim::kNoCandidate,n);
  Test(t.Begin(true,0x054c,0x0268,f2,18,prev.data(),8,host),n);
  Test(!t.OwnerDecision(false),n);
  Test(t.State()==EnrollmentState::kCancelled,n);
  Test(t.Begin(true,0x054c,0x0268,f2,18,prev.data(),8,host),n);
  Test(t.OwnerDecision(true),n);
  Test(!t.WriteResult(false),n);
  Test(t.State()==EnrollmentState::kCancelled,n);
  Test(t.Begin(true,0x054c,0x0268,f2,18,prev.data(),8,host),n);
  Test(t.OwnerDecision(true),n);
  Test(t.WriteResult(true),n);
  Test(!t.Readback(prev.data(),8),n);
  Test(t.State()==EnrollmentState::kCancelled,n);
  Test(t.Begin(true,0x054c,0x0268,f2,18,target.data(),8,host),n);
  Test(t.OwnerDecision(true),n);
  Test(t.State()==EnrollmentState::kAwaitReadback,n);
  Test(!t.RequestedWrite(),n);
  t.UsbDetached(); Test(t.State()==EnrollmentState::kCancelled,n);
  Test(t.Begin(true,0x054c,0x0268,f2,18,target.data(),8,host),n);
  Test(t.OwnerDecision(true),n);
  Test(t.Readback(target.data(),8),n);
  Test(t.CheckRadioAddress(ds3)==RadioClaim::kAddressCandidateNotAuthenticated,n);
  uint8_t invalid[18] = {0xf2};
  Test(!t.Begin(true,0x054c,0x0268,invalid,18,target.data(),8,host),n);
  Test(t.CheckRadioAddress(ds3)==RadioClaim::kNoCandidate,n);
  std::cout<<n<<"/"<<n<<" PASS (host-only USB enrollment transaction)\n";
}
