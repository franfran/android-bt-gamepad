#include "session_descriptor_envelope.h"

namespace retrobox {

DescriptorGate::DescriptorGate(size_t max_fixture_length)
    : max_fixture_length_(max_fixture_length) {}

Ticket DescriptorGate::Open(uint8_t hid_handle, bool native_policy_passed) {
  // Retire old generation even if the HID handle number is reused.
  Ticket ticket{hid_handle, ++next_generation_};
  candidates_[hid_handle] =
      Candidate{ticket, native_policy_passed, false, false, std::nullopt};
  return ticket;
}

DescriptorGate::Candidate* DescriptorGate::Current(Ticket ticket) {
  const auto it = candidates_.find(ticket.hid_handle);
  if (it == candidates_.end() || !(it->second.ticket == ticket)) return nullptr;
  return &it->second;
}

bool DescriptorGate::ReceiveDescriptor(Ticket ticket, const uint8_t* bytes,
                                       size_t length, bool fixture_gamepad_valid) {
  Candidate* c = Current(ticket);
  if (!c || !c->native_policy_passed || !fixture_gamepad_valid ||
      !bytes || length == 0 || length > max_fixture_length_ ||
      c->owned_descriptor || c->uhid_created) return false;
  // Important: never retain p_cb->dscp_info.descriptor.dsc_list as a borrowed ptr.
  c->owned_descriptor = std::vector<uint8_t>(bytes, bytes + length);
  return true;
}

bool DescriptorGate::JavaDecision(Ticket ticket, bool allowed) {
  Candidate* c = Current(ticket);
  if (!c) return false;
  if (!allowed) {
    candidates_.erase(ticket.hid_handle);
    return false;
  }
  if (!c->native_policy_passed) return false;
  c->java_allowed = true;
  return true;
}

std::optional<OwnedDescriptor> DescriptorGate::ReleaseUhidCreate(Ticket ticket) {
  Candidate* c = Current(ticket);
  if (!c || !c->native_policy_passed || !c->java_allowed ||
      !c->owned_descriptor || c->uhid_created) return std::nullopt;
  c->uhid_created = true;
  return OwnedDescriptor{ticket, *c->owned_descriptor};
}

bool DescriptorGate::AllowUhidInput(Ticket ticket, bool kernel_ready,
                                    bool fixture_report_valid) {
  Candidate* c = Current(ticket);
  return c && c->native_policy_passed && c->java_allowed && c->uhid_created &&
         kernel_ready && fixture_report_valid;
}

bool DescriptorGate::Close(Ticket ticket) {
  if (!Current(ticket)) return false;
  candidates_.erase(ticket.hid_handle);
  return true;
}

size_t DescriptorGate::ActiveCandidates() const { return candidates_.size(); }

}  // namespace retrobox
