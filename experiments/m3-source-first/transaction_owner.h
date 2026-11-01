#pragma once
// Offline-only C++17 model. NOT deployable M3 Bluetooth code.
// Every handle becomes quarantined after completion/disconnect/timeout:
// the native callback does NOT contain a request token or session epoch.
#include <cstdint>
#include <map>
#include <optional>
enum class Origin { KernelUhidSet, UhidOutputFeature, JavaHalSet, GetReport, SetProtocol };
enum class Phase { Idle, InFlight, Quarantined };
enum class CompletionKind { Handshake, LocalSendFailure };
struct Transaction { Origin origin; uint32_t kernel_id; uint64_t deadline; };
struct Observation { Origin origin; uint32_t kernel_id; uint8_t native_status; CompletionKind kind; };
class TransactionOwner {
 public:
  bool begin(uint16_t handle, Origin origin, uint32_t kernel_id, uint64_t now, uint64_t timeout) {
    auto& state = states_[handle];
    if (state.phase != Phase::Idle || timeout == 0 || timeout > UINT64_MAX - now) return false;
    if (origin != Origin::KernelUhidSet && kernel_id != 0) return false;
    state.phase = Phase::InFlight;
    state.transaction = Transaction{origin, kernel_id, now + timeout};
    return true;
  }
  std::optional<Observation> finish(uint16_t handle, uint8_t native_status, uint64_t now,
                                    CompletionKind kind) {
    auto it = states_.find(handle);
    if (it == states_.end() || it->second.phase != Phase::InFlight) return std::nullopt;
    auto& state = it->second;
    if (now >= state.transaction->deadline) { quarantine(state); return std::nullopt; }
    auto tx = *state.transaction;
    quarantine(state);
    // This is an observation, NOT a UHID kernel ACK or proof of callback attribution.
    return Observation{tx.origin, tx.kernel_id, native_status, kind};
  }
  void disconnect(uint16_t handle) { quarantine(states_[handle]); }
  bool expire(uint16_t handle, uint64_t now) {
    auto it = states_.find(handle);
    if (it == states_.end() || it->second.phase != Phase::InFlight ||
        now < it->second.transaction->deadline) return false;
    quarantine(it->second);
    return true;
  }
  Phase phase(uint16_t handle) const {
    auto it = states_.find(handle);
    return it == states_.end() ? Phase::Idle : it->second.phase;
  }
 private:
  struct State { Phase phase = Phase::Idle; std::optional<Transaction> transaction; };
  static void quarantine(State& s) { s.transaction.reset(); s.phase = Phase::Quarantined; }
  std::map<uint16_t, State> states_;
};
