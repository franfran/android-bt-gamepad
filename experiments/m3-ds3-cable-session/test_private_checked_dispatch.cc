#include "private_checked_dispatch.h"
#include "session_descriptor_envelope.h"
#include <cstddef>
#include <cstdint>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using namespace retrobox;

void Check(bool condition) {
  if (!condition) throw std::runtime_error("assertion failed");
}

struct Case { std::string name; std::function<void()> run; };

int main() {
  std::vector<Case> cases;
  cases.push_back({"posting success owns bytes until callback", [] {
    CheckedPrivateJniDispatcher d;
    DispatchLifetime life;
    uint8_t bytes[] = {3, 4};
    Check(d.Submit({5, 1}, bytes, 2, true, &life));
    Check(life.constructed == 1 && life.destroyed == 0);
    bytes[0] = 99;
    auto cb = [](DescriptorTicket t, const std::vector<uint8_t>& payload) {
      return t.handle == 5 && payload == std::vector<uint8_t>({3, 4});
    };
    Check(d.RunOne(cb));
    Check(d.Pending() == 0 && life.destroyed == 1);
  }});
  cases.push_back({"failed scheduler post cleans task", [] {
    CheckedPrivateJniDispatcher d;
    DispatchLifetime life;
    uint8_t bytes[] = {1};
    Check(!d.Submit({5, 1}, bytes, 1, false, &life));
    Check(d.Pending() == 0 && life.constructed == 1 && life.destroyed == 1);
  }});
  cases.push_back({"queue capacity rejection cleans task", [] {
    CheckedPrivateJniDispatcher d(1);
    DispatchLifetime life;
    uint8_t bytes[] = {1};
    Check(d.Submit({5, 1}, bytes, 1, true, &life));
    Check(!d.Submit({6, 1}, bytes, 1, true, &life));
    Check(life.constructed == 2 && life.destroyed == 1);
    d.Shutdown();
    Check(life.destroyed == 2 && d.Pending() == 0);
  }});
  cases.push_back({"invalid descriptor never allocates", [] {
    CheckedPrivateJniDispatcher d;
    DispatchLifetime life;
    Check(!d.Submit({5, 1}, nullptr, 2, true, &life));
    uint8_t bytes[] = {1};
    Check(!d.Submit({5, 0}, bytes, 1, true, &life));
    Check(life.constructed == 0 && life.destroyed == 0);
  }});
  cases.push_back({"revoke queued ticket releases memory", [] {
    CheckedPrivateJniDispatcher d;
    DispatchLifetime life;
    uint8_t bytes[] = {1};
    Check(d.Submit({5, 1}, bytes, 1, true, &life));
    Check(d.Submit({6, 1}, bytes, 1, true, &life));
    Check(d.Cancel({5, 1}) == 1);
    Check(d.Pending() == 1 && life.destroyed == 1);
    d.Shutdown();
    Check(life.destroyed == 2);
  }});
  cases.push_back({"stale callback refused by session gate", [] {
    CheckedPrivateJniDispatcher d;
    DescriptorGate gate;
    auto t = gate.Open(5, true);
    uint8_t bytes[] = {8};
    Check(d.Submit({t.hid_handle, t.generation}, bytes, 1, true));
    const auto t2 = gate.Open(5, true);
    auto cb = [&](DescriptorTicket tick, const std::vector<uint8_t>& payload) {
      return gate.ReceiveDescriptor({tick.handle, tick.generation}, payload.data(), payload.size(), true);
    };
    Check(!d.RunOne(cb));
    Check(gate.JavaDecision(t2, true));
    Check(!gate.ReleaseUhidCreate(t2));
  }});
  cases.push_back({"Java denial before queued delivery", [] {
    CheckedPrivateJniDispatcher d;
    DescriptorGate gate;
    auto t = gate.Open(5, true);
    uint8_t bytes[] = {7};
    Check(d.Submit({t.hid_handle, t.generation}, bytes, 1, true));
    Check(!gate.JavaDecision(t, false));
    auto cb = [&](DescriptorTicket tick, const std::vector<uint8_t>& payload) {
      return gate.ReceiveDescriptor({tick.handle, tick.generation}, payload.data(), payload.size(), true);
    };
    Check(!d.RunOne(cb));
  }});
  cases.push_back({"descriptor first waits for Java permission", [] {
    CheckedPrivateJniDispatcher d;
    DescriptorGate gate;
    auto t = gate.Open(5, true);
    uint8_t bytes[] = {1, 2};
    Check(d.Submit({t.hid_handle, t.generation}, bytes, 2, true));
    auto cb = [&](DescriptorTicket tick, const std::vector<uint8_t>& payload) {
      return gate.ReceiveDescriptor({tick.handle, tick.generation}, payload.data(), payload.size(), true);
    };
    Check(d.RunOne(cb));
    Check(!gate.ReleaseUhidCreate(t));
    Check(gate.JavaDecision(t, true));
    auto out = gate.ReleaseUhidCreate(t);
    Check(out && out->bytes == std::vector<uint8_t>({1, 2}));
  }});
  cases.push_back({"Java permission first waits for descriptor", [] {
    CheckedPrivateJniDispatcher d;
    DescriptorGate gate;
    auto t = gate.Open(5, true);
    Check(gate.JavaDecision(t, true));
    Check(!gate.ReleaseUhidCreate(t));
    uint8_t bytes[] = {1, 2};
    Check(d.Submit({t.hid_handle, t.generation}, bytes, 2, true));
    auto cb = [&](DescriptorTicket tick, const std::vector<uint8_t>& payload) {
      return gate.ReceiveDescriptor({tick.handle, tick.generation}, payload.data(), payload.size(), true);
    };
    Check(d.RunOne(cb));
    Check(gate.ReleaseUhidCreate(t).has_value());
  }});
  cases.push_back({"parallel device events remain isolated", [] {
    CheckedPrivateJniDispatcher d;
    DescriptorGate gate;
    const auto a = gate.Open(5, true), b = gate.Open(6, true);
    uint8_t da[] = {1}, db[] = {2};
    Check(d.Submit({a.hid_handle, a.generation}, da, 1, true));
    Check(d.Submit({b.hid_handle, b.generation}, db, 1, true));
    auto cb = [&](DescriptorTicket tick, const std::vector<uint8_t>& payload) {
      return gate.ReceiveDescriptor({tick.handle, tick.generation}, payload.data(), payload.size(), true);
    };
    Check(d.RunOne(cb)); Check(d.RunOne(cb));
    Check(gate.JavaDecision(b, true)); Check(gate.JavaDecision(a, true));
    auto ra = gate.ReleaseUhidCreate(a), rb = gate.ReleaseUhidCreate(b);
    Check(ra && rb && ra->bytes[0] == 1 && rb->bytes[0] == 2);
  }});
  cases.push_back({"rejected consumer still destroys event", [] {
    CheckedPrivateJniDispatcher d;
    DispatchLifetime life;
    uint8_t bytes[] = {4};
    Check(d.Submit({5, 1}, bytes, 1, true, &life));
    auto deny = [](DescriptorTicket, const std::vector<uint8_t>&) { return false; };
    Check(!d.RunOne(deny));
    Check(life.constructed == 1 && life.destroyed == 1);
  }});
  cases.push_back({"shutdown cancels all messages", [] {
    CheckedPrivateJniDispatcher d;
    DispatchLifetime life;
    uint8_t bytes[] = {4};
    for (uint8_t h = 1; h <= 4; ++h)
      Check(d.Submit({h, 1}, bytes, 1, true, &life));
    Check(d.Pending() == 4);
    d.Shutdown();
    Check(d.Pending() == 0 && life.constructed == 4 && life.destroyed == 4);
  }});
  size_t run = 0;
  for (const auto& entry : cases) {
    try { entry.run(); ++run; }
    catch (const std::exception& ex) {
      std::cerr << "FAIL " << entry.name << ": " << ex.what() << "\n";
      return 1;
    }
  }
  std::cout << run << "/" << cases.size() << " PASS (checked private JNI dispatcher model)\n";
}
