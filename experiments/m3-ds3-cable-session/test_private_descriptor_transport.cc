#include "private_descriptor_transport.h"
#include "session_descriptor_envelope.h"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using retrobox::DescriptorTicket;
using retrobox::PrivateDescriptorTransport;

struct Capture {
  std::vector<std::string> seen;
  bool accept = true;
  uint64_t expected_generation = 1;
  bool operator()(DescriptorTicket t, const std::vector<uint8_t>& bytes, bool valid) {
    if (!accept || !valid || t.generation != expected_generation) return false;
    seen.push_back(std::to_string(t.handle) + ":" + std::to_string(bytes.at(0)));
    return true;
  }
};

int main() {
  int count = 0;
  auto verify = [&](bool okay) { if (!okay) throw std::runtime_error("test failed #" + std::to_string(count + 1)); ++count; };
  const DescriptorTicket a{3, 1}, b{4, 1}, a2{3, 2};
  uint8_t bytes[] = {10, 20, 30};
  {
    PrivateDescriptorTransport q;
    Capture c;
    verify(q.Submit(a, bytes, sizeof(bytes), true));
    bytes[0] = 99;  // BTA producer may mutate/free original bytes after transfer.
    verify(q.DispatchOne(c) && c.seen[0] == "3:10");
    verify(q.Pending() == 0);
    verify(!q.DispatchOne(c));
  }
  {
    PrivateDescriptorTransport q;
    Capture c;
    uint8_t p[] = {1}, r[] = {2};
    verify(q.Submit(a, p, 1, true));
    verify(q.Submit(b, r, 1, true));
    verify(q.DispatchOne(c) && q.DispatchOne(c));
    verify(c.seen == std::vector<std::string>({"3:1", "4:2"}));
  }
  {
    PrivateDescriptorTransport q;
    Capture c;
    uint8_t p[] = {1};
    verify(q.Submit(a, p, 1, true));
    verify(!q.Submit(a, p, 1, true));
    verify(q.Cancel(a) == 1 && q.Pending() == 0);
    verify(!q.DispatchOne(c));
  }
  {
    PrivateDescriptorTransport q;
    Capture c;
    uint8_t p[] = {1};
    verify(q.Submit(a, p, 1, true));
    verify(q.Submit(a2, p, 1, true));
    verify(q.Cancel(a) == 1 && q.Pending() == 1);
    c.expected_generation = 2;
    verify(q.DispatchOne(c) && c.seen.size() == 1);
  }
  {
    PrivateDescriptorTransport q;
    Capture c;
    uint8_t p[] = {1};
    verify(q.Submit(a, p, 1, false));
    verify(!q.DispatchOne(c) && q.Pending() == 0);
    c.accept = false;
    verify(q.Submit(a, p, 1, true));
    verify(!q.DispatchOne(c) && q.Pending() == 0);
  }
  {
    PrivateDescriptorTransport q(2, 1);
    uint8_t p[] = {1, 2, 3};
    verify(!q.Submit(a, nullptr, 1, true));
    verify(!q.Submit(a, p, 0, true));
    verify(!q.Submit(a, p, 3, true));
    verify(q.Submit(a, p, 2, true));
    verify(!q.Submit(b, p, 2, true));
    q.CancelAll();
    verify(q.Pending() == 0);
  }
  {
    PrivateDescriptorTransport q;
    Capture c;
    uint8_t p[] = {1};
    verify(q.Submit(a, p, 1, true));
    c.expected_generation = 2; // old event queued, consumer's live epoch differs.
    verify(!q.DispatchOne(c) && c.seen.empty());
  }
  {
    // Integration with prior compiled session-bound gate: no Java approval
    // means the private descriptor may arrive but no UHID_CREATE is released.
    PrivateDescriptorTransport q;
    retrobox::DescriptorGate gate;
    auto t = gate.Open(3, true);
    uint8_t p[] = {5, 6};
    verify(q.Submit({t.hid_handle, t.generation}, p, 2, true));
    auto deliver = [&](DescriptorTicket tok, const std::vector<uint8_t>& buf, bool valid) {
      return gate.ReceiveDescriptor({tok.handle, tok.generation}, buf.data(), buf.size(), valid);
    };
    verify(q.DispatchOne(deliver));
    verify(!gate.ReleaseUhidCreate(t));
    verify(gate.JavaDecision(t, true));
    auto result = gate.ReleaseUhidCreate(t);
    verify(result && result->bytes == std::vector<uint8_t>({5, 6}));
  }
  {
    PrivateDescriptorTransport q;
    retrobox::DescriptorGate gate;
    auto t_old = gate.Open(3, true);
    uint8_t p[] = {5};
    verify(q.Submit({t_old.hid_handle, t_old.generation}, p, 1, true));
    auto t_new = gate.Open(3, true);
    auto deliver = [&](DescriptorTicket tok, const std::vector<uint8_t>& buf, bool valid) {
      return gate.ReceiveDescriptor({tok.handle, tok.generation}, buf.data(), buf.size(), valid);
    };
    verify(!q.DispatchOne(deliver));
    verify(gate.JavaDecision(t_new, true));
    verify(!gate.ReleaseUhidCreate(t_new));
  }
  std::cout << count << "/" << count << " checks PASS (host-only copy/queue model)\n";
}
