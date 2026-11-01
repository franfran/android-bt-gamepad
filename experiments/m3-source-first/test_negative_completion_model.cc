#include "negative_completion_model.h"
#include <cassert>
#include <iostream>
int main() {
  using F=FailureSite;
  const F failures[]={F::Allocation,F::InvalidHandle,F::NoAcl,F::Congestion,F::SendError,F::RemoteNegative,F::Timeout};
  for(unsigned i=0;i<sizeof(failures)/sizeof(failures[0]);++i) {
    NegativeCompletionModel m;
    assert(m.begin(1,40,100+i));
    assert(!m.fail(1,41,failures[i])); // wrong generation
    auto receipt=m.fail(1,40,failures[i]);
    assert(receipt && receipt->request_id==100+i && receipt->generation==40);
    assert(!m.fail(1,40,failures[i])); // exactly once
    assert(m.quarantined(1));
    assert(!m.begin(1,41,999)); // no unsafe handle reuse
    assert(m.begin(2,41,333)); // per-handle isolation
    assert(m.fail(2,41,F::SendError)->request_id==333);
  }
  NegativeCompletionModel d;
  assert(d.begin(3,5,0xffffffffu));
  d.disconnect(3);
  assert(!d.fail(3,5,F::RemoteNegative));
  assert(!d.begin(3,6,1));
  std::cout<<"negative completion ownership diagnostics PASS\n";
}
