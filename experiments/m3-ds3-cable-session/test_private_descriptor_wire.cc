#include "private_descriptor_wire.h"
#include "session_descriptor_envelope.h"
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace retrobox;
int main() {
  int checks = 0;
  auto check = [&](bool ok) { if (!ok) throw std::runtime_error("check failed " + std::to_string(checks + 1)); ++checks; };
  DescriptorTicket t{3, 1};
  uint8_t d[] = {0x11, 0x22, 0x33};
  auto encoded = PrivateDescriptorWire::Encode(t, d, sizeof(d));
  check(encoded && encoded->size() == 19);
  check(encoded->at(0) == 'R' && encoded->at(4) == 1);
  check(encoded->at(6) == 1 && encoded->at(14) == 3);
  d[0] = 0x99; // byte snapshot already independent
  auto decoded = PrivateDescriptorWire::Decode(*encoded);
  check(decoded && decoded->ticket.handle == 3 && decoded->ticket.generation == 1);
  check(decoded->descriptor == std::vector<uint8_t>({0x11, 0x22, 0x33}));
  {
    auto bad = *encoded;
    bad[0] = 'X'; check(!PrivateDescriptorWire::Decode(bad));
    bad = *encoded; bad[4] = 99; check(!PrivateDescriptorWire::Decode(bad));
    bad = *encoded; bad[6] = 0; check(!PrivateDescriptorWire::Decode(bad));
    bad = *encoded; bad[14] = 0; check(!PrivateDescriptorWire::Decode(bad));
    bad = *encoded; bad.push_back(0); check(!PrivateDescriptorWire::Decode(bad));
    bad = *encoded; bad.pop_back(); check(!PrivateDescriptorWire::Decode(bad));
    bad = *encoded; bad[15] = 0x20; check(!PrivateDescriptorWire::Decode(bad));
  }
  check(!PrivateDescriptorWire::Decode({}));
  check(!PrivateDescriptorWire::Encode(t, nullptr, 3));
  check(!PrivateDescriptorWire::Encode(t, d, 0));
  check(!PrivateDescriptorWire::Encode({3, 0}, d, 3));
  {
    PrivateWireQueue queue(1);
    check(!queue.Post(t, d, 3, false));
    check(queue.Pending() == 0);
    check(queue.Post(t, d, 3));
    check(!queue.Post({4, 1}, d, 3));
    queue.CancelAll(); check(queue.Pending() == 0);
  }
  {
    // Old HID handle event cannot be attached to the new generation.
    DescriptorGate gate;
    PrivateWireQueue queue;
    auto old_ticket = gate.Open(3, true);
    uint8_t bytes[] = {1};
    check(queue.Post({old_ticket.hid_handle, old_ticket.generation}, bytes, 1));
    auto fresh = gate.Open(3, true);
    auto consumer = [&](DescriptorTicket tt, const std::vector<uint8_t>& v) {
      return gate.ReceiveDescriptor({tt.handle, tt.generation}, v.data(), v.size(), true);
    };
    check(!queue.DispatchOne(consumer));
    check(gate.JavaDecision(fresh, true));
    check(!gate.ReleaseUhidCreate(fresh));
    check(queue.Post({fresh.hid_handle, fresh.generation}, bytes, 1));
    check(queue.DispatchOne(consumer));
    auto out = gate.ReleaseUhidCreate(fresh);
    check(out && out->bytes == std::vector<uint8_t>({1}));
  }
  {
    // Java denial destroys candidate; later descriptor delivery cannot grant.
    DescriptorGate gate;
    PrivateWireQueue queue;
    auto ticket = gate.Open(5, true);
    uint8_t bytes[] = {9};
    check(queue.Post({ticket.hid_handle, ticket.generation}, bytes, 1));
    check(!gate.JavaDecision(ticket, false));
    auto consumer = [&](DescriptorTicket tt, const std::vector<uint8_t>& v) {
      return gate.ReceiveDescriptor({tt.handle, tt.generation}, v.data(), v.size(), true);
    };
    check(!queue.DispatchOne(consumer) && queue.Pending() == 0);
  }
  std::cout << checks << "/" << checks << " checks PASS (pointer-free byte wire model)\n";
}
