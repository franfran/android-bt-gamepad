#include "session_descriptor_envelope.h"

#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using retrobox::DescriptorGate;
using retrobox::Ticket;

static void Check(bool result) {
  if (!result) throw std::runtime_error("unexpected admission gate result");
}

int main() {
  std::vector<std::pair<std::string, std::function<void()>>> tests;
  tests.emplace_back("descriptor-first must await Java", [] {
    DescriptorGate g;
    auto t = g.Open(4, true);
    const uint8_t desc[] = {1, 2, 3};
    Check(g.ReceiveDescriptor(t, desc, sizeof(desc), true));
    Check(!g.ReleaseUhidCreate(t));
    Check(g.JavaDecision(t, true));
    Check(g.ReleaseUhidCreate(t).has_value());
  });
  tests.emplace_back("Java-first must await descriptor", [] {
    DescriptorGate g;
    auto t = g.Open(4, true);
    Check(g.JavaDecision(t, true));
    Check(!g.ReleaseUhidCreate(t));
    const uint8_t d[] = {4};
    Check(g.ReceiveDescriptor(t, d, sizeof(d), true));
    Check(g.ReleaseUhidCreate(t).has_value());
  });
  tests.emplace_back("own bytes after original producer mutation", [] {
    DescriptorGate g;
    auto t = g.Open(4, true);
    std::vector<uint8_t> producer{1, 2, 3};
    Check(g.ReceiveDescriptor(t, producer.data(), producer.size(), true));
    producer.assign({9, 9, 9});
    Check(g.JavaDecision(t, true));
    auto output = g.ReleaseUhidCreate(t);
    Check(output && output->bytes == std::vector<uint8_t>({1, 2, 3}));
  });
  tests.emplace_back("native veto blocks both descriptor and Java", [] {
    DescriptorGate g;
    auto t = g.Open(4, false);
    const uint8_t d[] = {1};
    Check(!g.ReceiveDescriptor(t, d, sizeof(d), true));
    Check(!g.JavaDecision(t, true));
    Check(!g.ReleaseUhidCreate(t));
  });
  tests.emplace_back("invalid fixture descriptor blocked", [] {
    DescriptorGate g;
    auto t = g.Open(4, true);
    const uint8_t d[] = {1};
    Check(!g.ReceiveDescriptor(t, d, sizeof(d), false));
    Check(g.JavaDecision(t, true));
    Check(!g.ReleaseUhidCreate(t));
  });
  tests.emplace_back("null descriptor blocked", [] {
    DescriptorGate g;
    auto t = g.Open(4, true);
    Check(!g.ReceiveDescriptor(t, nullptr, 2, true));
  });
  tests.emplace_back("empty descriptor blocked", [] {
    DescriptorGate g;
    auto t = g.Open(4, true);
    uint8_t d[] = {1};
    Check(!g.ReceiveDescriptor(t, d, 0, true));
  });
  tests.emplace_back("fixture length upper bound blocked", [] {
    DescriptorGate g(2);
    auto t = g.Open(4, true);
    uint8_t d[] = {1, 2, 3};
    Check(!g.ReceiveDescriptor(t, d, sizeof(d), true));
  });
  tests.emplace_back("duplicate descriptor does not replace original", [] {
    DescriptorGate g;
    auto t = g.Open(4, true);
    uint8_t first[] = {1}, second[] = {2};
    Check(g.ReceiveDescriptor(t, first, sizeof(first), true));
    Check(!g.ReceiveDescriptor(t, second, sizeof(second), true));
    Check(g.JavaDecision(t, true));
    auto out = g.ReleaseUhidCreate(t);
    Check(out && out->bytes[0] == 1);
  });
  tests.emplace_back("UHID CREATE released at most once", [] {
    DescriptorGate g;
    auto t = g.Open(4, true);
    uint8_t d[] = {1};
    Check(g.ReceiveDescriptor(t, d, sizeof(d), true));
    Check(g.JavaDecision(t, true));
    Check(g.ReleaseUhidCreate(t).has_value());
    Check(!g.ReleaseUhidCreate(t));
  });
  tests.emplace_back("interleaved devices preserve destination", [] {
    DescriptorGate g;
    auto a = g.Open(4, true);
    auto b = g.Open(5, true);
    uint8_t da[] = {0xa}, db[] = {0xb};
    Check(g.ReceiveDescriptor(a, da, sizeof(da), true));
    Check(g.ReceiveDescriptor(b, db, sizeof(db), true));
    Check(g.JavaDecision(b, true));
    Check(g.JavaDecision(a, true));
    auto oa = g.ReleaseUhidCreate(a), ob = g.ReleaseUhidCreate(b);
    Check(oa && ob && oa->ticket == a && ob->ticket == b);
    Check(oa->bytes[0] == 0xa && ob->bytes[0] == 0xb);
  });
  tests.emplace_back("stale event after HID handle reuse blocked", [] {
    DescriptorGate g;
    auto stale = g.Open(4, true);
    auto fresh = g.Open(4, true);
    uint8_t d[] = {1};
    Check(!g.ReceiveDescriptor(stale, d, sizeof(d), true));
    Check(!g.JavaDecision(stale, false));
    Check(g.ReceiveDescriptor(fresh, d, sizeof(d), true));
    Check(g.JavaDecision(fresh, true));
    Check(g.ReleaseUhidCreate(fresh).has_value());
  });
  tests.emplace_back("Java denial destroys owned descriptor state", [] {
    DescriptorGate g;
    auto t = g.Open(4, true);
    uint8_t d[] = {1};
    Check(g.ReceiveDescriptor(t, d, sizeof(d), true));
    Check(!g.JavaDecision(t, false));
    Check(g.ActiveCandidates() == 0);
    Check(!g.ReleaseUhidCreate(t));
  });
  tests.emplace_back("disconnect revokes subsequent UHID input", [] {
    DescriptorGate g;
    auto t = g.Open(4, true);
    uint8_t d[] = {1};
    Check(g.ReceiveDescriptor(t, d, sizeof(d), true));
    Check(g.JavaDecision(t, true));
    Check(g.ReleaseUhidCreate(t).has_value());
    Check(g.AllowUhidInput(t, true, true));
    Check(g.Close(t));
    Check(!g.AllowUhidInput(t, true, true));
  });
  tests.emplace_back("UHID kernel-ready never substitutes for admission", [] {
    DescriptorGate g;
    auto t = g.Open(4, true);
    Check(!g.AllowUhidInput(t, true, true));
  });
  tests.emplace_back("reports require kernel ready and fixture gate", [] {
    DescriptorGate g;
    auto t = g.Open(4, true);
    uint8_t d[] = {1};
    Check(g.ReceiveDescriptor(t, d, sizeof(d), true));
    Check(g.JavaDecision(t, true));
    Check(g.ReleaseUhidCreate(t).has_value());
    Check(!g.AllowUhidInput(t, false, true));
    Check(!g.AllowUhidInput(t, true, false));
    Check(g.AllowUhidInput(t, true, true));
  });
  tests.emplace_back("closing stale ticket does not kill new session", [] {
    DescriptorGate g;
    auto old = g.Open(4, true);
    auto fresh = g.Open(4, true);
    Check(!g.Close(old));
    Check(g.ActiveCandidates() == 1);
    Check(g.Close(fresh));
    Check(g.ActiveCandidates() == 0);
  });
  int count = 0;
  for (auto& test : tests) {
    try { test.second(); ++count; }
    catch (const std::exception& e) {
      std::cerr << "FAIL " << test.first << ": " << e.what() << '\n';
      return 1;
    }
  }
  std::cout << count << "/" << tests.size() << " PASS (host-only C++ model)\n";
  return 0;
}
