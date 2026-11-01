#include "ingress_origin_owner.h"
#include <cassert>
#include <iostream>
int main() {
  IngressOwner owner;
  using O=IngressOrigin;
  using A=Admission;
  assert(owner.enter(1,{O::KernelSet,52,10})==A::Accepted);
  assert(owner.enter(1,{O::KernelOutputFeature,0,10})==A::Busy);
  assert(owner.enter(1,{O::JavaHal,0,10})==A::Busy);
  assert(!owner.local_failure(1,11));
  auto failure=owner.local_failure(1,10);
  assert(failure && failure->origin==O::KernelSet && failure->kernel_id==52);
  assert(!owner.local_failure(1,10));
  assert(owner.enter(1,{O::KernelSet,53,11})==A::Quarantined);
  assert(owner.enter(2,{O::KernelOutputFeature,1,10})==A::InvalidOrigin);
  assert(owner.enter(2,{O::KernelOutputFeature,0,10})==A::Accepted);
  assert(owner.local_failure(2,10)->origin==O::KernelOutputFeature);
  assert(owner.enter(3,{O::JavaHal,0,20})==A::Accepted);
  owner.disconnect(3);
  assert(!owner.local_failure(3,20));
  std::cout << "source-origin admission host contract PASS\n";
}
