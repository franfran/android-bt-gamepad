// Host-only, NO USB I/O. Cable evidence is NOT a Bluetooth authentication grant.
#ifndef RETROBOX_DS3_USB_ENROLLMENT_H_
#define RETROBOX_DS3_USB_ENROLLMENT_H_
#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>

namespace retrobox {
using BdAddr = std::array<uint8_t, 6>;

inline bool ValidAddress(const BdAddr& addr) {
  bool all_zero = true, all_ff = true;
  for (auto v : addr) { all_zero &= (v == 0); all_ff &= (v == 255); }
  return !all_zero && !all_ff;
}

// Based on public BlueZ sixaxis USB report offsets; no source copied.
inline std::optional<BdAddr> ParseDs3F2(const uint8_t* data, size_t size) {
  if (!data || size != 18 || data[0] != 0xf2) return std::nullopt;
  BdAddr result{};
  for (size_t i = 0; i < 6; ++i) result[i] = data[9 - i];
  return ValidAddress(result) ? std::optional<BdAddr>(result) : std::nullopt;
}
inline std::optional<BdAddr> ParseDs3F5(const uint8_t* data, size_t size) {
  if (!data || size != 8 || data[0] != 0xf5) return std::nullopt;
  BdAddr result{};
  for (size_t i = 0; i < 6; ++i) result[i] = data[7 - i];
  return ValidAddress(result) ? std::optional<BdAddr>(result) : std::nullopt;
}
inline std::array<uint8_t, 8> BuildDs3F5Write(const BdAddr& host) {
  std::array<uint8_t, 8> report{{0xf5, 0x01, 0, 0, 0, 0, 0, 0}};
  for (size_t i = 0; i < 6; ++i) report[i + 2] = host[5 - i];
  return report;
}

enum class EnrollmentState { kIdle, kAwaitOwner, kAwaitWrite, kAwaitReadback,
                             kCommitted, kCancelled };
enum class RadioClaim { kNoCandidate, kAddressCandidateNotAuthenticated };

class UsbEnrollmentTransaction {
 public:
  // trusted_usb_transport must eventually be established by a privileged,
  // local USB backend, not caller-controlled app input or Bluetooth metadata.
  bool Begin(bool trusted_usb_transport, uint16_t vid, uint16_t pid,
             const uint8_t* f2, size_t f2_len, const uint8_t* f5, size_t f5_len,
             BdAddr local_adapter) {
    Reset();
    if (!trusted_usb_transport || vid != 0x054c || pid != 0x0268 ||
        !ValidAddress(local_adapter)) return false;
    auto device = ParseDs3F2(f2, f2_len);
    auto current_host = ParseDs3F5(f5, f5_len);
    if (!device || !current_host || *device == local_adapter) return false;
    device_ = *device;
    local_host_ = local_adapter;
    currently_programmed_host_ = *current_host;
    state_ = EnrollmentState::kAwaitOwner;
    return true;
  }
  bool OwnerDecision(bool approved) {
    if (state_ != EnrollmentState::kAwaitOwner) return false;
    if (!approved) { Cancel(); return false; }
    state_ = currently_programmed_host_ == local_host_
                 ? EnrollmentState::kAwaitReadback
                 : EnrollmentState::kAwaitWrite;
    return true;
  }
  std::optional<std::array<uint8_t, 8>> RequestedWrite() const {
    if (state_ != EnrollmentState::kAwaitWrite) return std::nullopt;
    return BuildDs3F5Write(local_host_);
  }
  bool WriteResult(bool successful) {
    if (state_ != EnrollmentState::kAwaitWrite) return false;
    if (!successful) { Cancel(); return false; }
    state_ = EnrollmentState::kAwaitReadback;
    return true;
  }
  bool Readback(const uint8_t* report, size_t size) {
    if (state_ != EnrollmentState::kAwaitReadback) return false;
    auto host = ParseDs3F5(report, size);
    if (!host || *host != local_host_) { Cancel(); return false; }
    state_ = EnrollmentState::kCommitted;
    return true;
  }
  void UsbDetached() {
    if (state_ != EnrollmentState::kCommitted) Cancel();
    // A finished cable enrollment remains as a limited radio candidate.
  }
  void AdapterChanged(const BdAddr& current) {
    if (state_ != EnrollmentState::kIdle && current != local_host_) Cancel();
  }
  void Cancel() {
    device_.fill(0);
    local_host_.fill(0);
    currently_programmed_host_.fill(0);
    state_ = EnrollmentState::kCancelled;
  }
  void Reset() {
    device_.fill(0);
    local_host_.fill(0);
    currently_programmed_host_.fill(0);
    state_ = EnrollmentState::kIdle;
  }
  EnrollmentState State() const { return state_; }
  RadioClaim CheckRadioAddress(const BdAddr& claimed) const {
    return state_ == EnrollmentState::kCommitted && claimed == device_
          ? RadioClaim::kAddressCandidateNotAuthenticated
          : RadioClaim::kNoCandidate;
  }
  // Deliberately NO AllowHid, GrantBond or BtmSuccess API.
 private:
  EnrollmentState state_ = EnrollmentState::kIdle;
  BdAddr device_{};
  BdAddr local_host_{};
  BdAddr currently_programmed_host_{};
};
}  // namespace retrobox
#endif
