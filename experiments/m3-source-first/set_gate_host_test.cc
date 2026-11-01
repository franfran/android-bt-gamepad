// Offline-only UHID SET_REPORT transaction model; NOT a Bluetooth patch.
// Callback carries only device handle + status, NO request ID or epoch.
// Attribution is conditional on external proof of strict completion ordering.
// After timeout/disconnect, the same device key is permanently quarantined.
#include <cassert>
#include <cstdint>
#include <limits>
#include <map>
#include <optional>
#include <set>

struct SetCompletion {
  uint32_t request_id;
  uint8_t raw_status; // Preserve status; NO fabricated UHID success.
};
struct PendingSet {
  uint32_t id;
  uint64_t deadline;
};
class SetGate {
 public:
  bool submit(uint16_t device, uint32_t id, uint64_t now, uint64_t timeout) {
    if (!timeout || quarantined(device) || pending_.count(device)) return false;
    if (timeout > std::numeric_limits<uint64_t>::max() - now) return false;
    pending_[device] = {id, now + timeout};
    return true;
  }
  std::optional<SetCompletion> complete(uint16_t device, uint8_t status, uint64_t now) {
    if (quarantined(device)) return std::nullopt;
    auto it = pending_.find(device);
    if (it == pending_.end()) return std::nullopt;
    if (now >= it->second.deadline) {
      pending_.erase(it);
      poisoned_.insert(device);
      return std::nullopt;
    }
    const auto id = it->second.id;
    pending_.erase(it);
    return SetCompletion{id, status};
  }
  bool expire(uint16_t device, uint64_t now) {
    auto it = pending_.find(device);
    if (it == pending_.end() || now < it->second.deadline) return false;
    pending_.erase(it);
    poisoned_.insert(device);
    return true;
  }
  void disconnect(uint16_t device) {
    pending_.erase(device);
    poisoned_.insert(device);
  }
  bool quarantined(uint16_t device) const { return poisoned_.count(device) != 0; }
  bool pending(uint16_t device) const { return pending_.count(device) != 0; }
 private:
  std::map<uint16_t, PendingSet> pending_;
  std::set<uint16_t> poisoned_;
};

int main() {
  SetGate g;
  assert(!g.complete(1, 0, 0));                            // unsolicited
  assert(g.submit(1, 0xffffffffU, 0, 5));                  // full ID range
  assert(!g.submit(1, 2, 1, 5));                           // parallel blocked
  assert(!g.expire(1, 4));                                 // before deadline
  auto c = g.complete(1, 7, 4);                             // negative status kept
  assert(c && c->request_id == 0xffffffffU && c->raw_status == 7);
  assert(!g.complete(1, 0, 4));                            // duplicate
  assert(g.submit(2, 22, 0, 5));
  assert(g.submit(3, 33, 0, 5));                            // distinct devices
  assert(g.complete(3, 0, 1)->request_id == 33);            // independent
  assert(g.expire(2, 5));
  assert(g.quarantined(2));
  assert(!g.complete(2, 0, 6));                            // late callback
  assert(!g.submit(2, 44, 7, 5));                          // no recycle
  assert(g.submit(4, 4, 0, 5));
  assert(!g.complete(4, 0, 5));                            // boundary timeout
  assert(g.quarantined(4));
  assert(g.submit(5, 5, 0, 5));
  g.disconnect(5);
  assert(!g.complete(5, 0, 1));
  assert(!g.submit(5, 6, 2, 5));                           // reconnect blocked
  assert(!g.submit(6, 6, 0, 0));                           // zero timeout
  assert(!g.submit(6, 6, UINT64_MAX, 1));                  // overflow
  assert(g.submit(7, 7, 0, 10));
  assert(g.complete(7, 0, 9)->request_id == 7);
  // LIMIT: no test can prove that a callback while a request is pending
  // actually corresponds to that request; native callback lacks a token.
}
