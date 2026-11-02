#include "acl_epoch_observer.h"
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using retrobox::AclEpochObserver;
using retrobox::AclObservationTicket;
static void Verify(bool ok) {
  if (!ok) throw std::runtime_error("ACL observer invariant failed");
}
int main() {
  std::vector<std::pair<std::string, std::function<void()>>> tests;
  tests.push_back({"fresh success emits nonzero generation", [] {
    AclEpochObserver o; auto t=o.Connected(7, 0x1100);
    Verify(t && t->generation != 0 && t->hci_handle==7);
    Verify(o.Current(7,0x1100)==t);
  }});
  tests.push_back({"HCI handle reused by a different LCB", [] {
    AclEpochObserver o; auto a=o.Connected(7,0x1100);
    auto b=o.Connected(7,0x2200);
    Verify(a && b && a->generation!=b->generation);
    Verify(!o.Current(7,0x1100) && o.Current(7,0x2200)==b);
    Verify(!o.Retire(*a));
  }});
  tests.push_back({"same LCB reused with new HCI handle", [] {
    AclEpochObserver o; auto a=o.Connected(7,0x1100);
    auto b=o.Connected(8,0x1100);
    Verify(a && b && b->generation>a->generation);
    Verify(!o.Current(7,0x1100) && o.Current(8,0x1100)==b);
  }});
  tests.push_back({"same handle and LCB still new epoch on reconnect", [] {
    AclEpochObserver o; auto a=o.Connected(7,0x1100);
    auto b=o.Connected(7,0x1100);
    Verify(a && b && b->generation>a->generation);
    Verify(!o.Retire(*a) && o.Current(7,0x1100)==b);
  }});
  tests.push_back({"retirement revokes only matched ticket", [] {
    AclEpochObserver o; auto a=o.Connected(7,0x1100);
    auto b=o.Connected(8,0x2200);
    Verify(a && b && o.Retire(*a));
    Verify(!o.Current(7,0x1100) && o.Current(8,0x2200)==b);
    Verify(!o.Retire(*a));
  }});
  tests.push_back({"retire after reused handle cannot kill new link", [] {
    AclEpochObserver o; auto a=o.Connected(7,0x1100);
    auto b=o.Connected(7,0x1100);
    Verify(a && b && !o.Retire(*a) && o.Current(7,0x1100)==b);
  }});
  tests.push_back({"mismatched pointer refuses current lookup", [] {
    AclEpochObserver o; Verify(o.Connected(7,0x1100).has_value());
    Verify(!o.Current(7,0x2200) && !o.Current(8,0x1100));
  }});
  tests.push_back({"invalid HCI handle refused", [] {
    AclEpochObserver o; Verify(!o.Connected(0xffff,0x1100));
    Verify(!o.Current(0xffff,0x1100));
  }});
  tests.push_back({"null LCB identity refused", [] {
    AclEpochObserver o; Verify(!o.Connected(7,0));
    Verify(!o.Current(7,0));
  }});
  tests.push_back({"full table never evicts unrelated session", [] {
    AclEpochObserver o(1); auto a=o.Connected(7,0x1100);
    Verify(a && !o.Connected(8,0x2200));
    Verify(o.Current(7,0x1100)==a);
  }});
  tests.push_back({"zero capacity fails closed", [] {
    AclEpochObserver o(0); Verify(!o.Connected(7,0x1100));
  }});
  tests.push_back({"retired slot can be reused without epoch reuse", [] {
    AclEpochObserver o(1); auto a=o.Connected(7,0x1100);
    Verify(a && o.Retire(*a));
    auto b=o.Connected(8,0x2200);
    Verify(b && b->generation>a->generation);
  }});
  tests.push_back({"clear retires entries while preserving generation counter", [] {
    AclEpochObserver o; auto a=o.Connected(7,0x1100);
    Verify(a.has_value()); o.Clear();
    Verify(!o.Current(7,0x1100));
    auto b=o.Connected(7,0x1100);
    Verify(b && b->generation>a->generation);
  }});
  tests.push_back({"separate handles can observe same PSM without identity mixing", [] {
    AclEpochObserver o; auto a=o.Connected(7,0x1100);
    auto b=o.Connected(8,0x2200);
    constexpr uint16_t hid_control=0x11;
    Verify(a && b && hid_control==0x11 && a->generation!=b->generation);
    Verify(o.Current(7,0x1100)==a && o.Current(8,0x2200)==b);
  }});
  size_t passed=0;
  for (const auto& t : tests) {
    try { t.second(); ++passed; }
    catch(const std::exception& e) {
      std::cerr << "FAIL " << t.first << ": " << e.what() << '\n';
      return 1;
    }
  }
  std::cout << passed << '/' << tests.size() << " PASS (host-only ACL epoch observer)\n";
}
