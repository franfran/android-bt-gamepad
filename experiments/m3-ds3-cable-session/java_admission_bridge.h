// Host-only JNI/Java ticket admission contract; NOT Android JNI or BTM policy.
#ifndef RETROBOX_JAVA_ADMISSION_BRIDGE_H_
#define RETROBOX_JAVA_ADMISSION_BRIDGE_H_
#include <cstddef>
#include <cstdint>
#include <optional>
#include <unordered_map>

namespace retrobox {
struct JavaTicket {
  uint8_t handle;
  uint64_t acl_epoch;
  uint64_t service_generation;
  uint64_t request_id;
  bool operator==(const JavaTicket& other) const {
    return handle == other.handle && acl_epoch == other.acl_epoch &&
           service_generation == other.service_generation &&
           request_id == other.request_id;
  }
};

enum class NativeEvidence { kVerifiedStandard, kCableCandidateUnverified };
enum class JavaVerdict { kAcceptStandard, kDeny, kCableReviewOnly };

// A *model* of pre-UHID approval, separate from existing connected-state HAL.
class JavaAdmissionBridge {
 public:
  void ServiceStarted() {
    ++service_generation_;
    active_ = true;
    sessions_.clear();  // old Java service can never approve a new session
  }
  void ServiceStopped() {
    active_ = false;
    sessions_.clear();
  }

  std::optional<JavaTicket> Offer(uint8_t handle, uint64_t acl_epoch,
                                   NativeEvidence native_evidence) {
    if (!active_ || !acl_epoch || handle == 0xff ||
        request_id_ == UINT64_MAX) return std::nullopt;
    JavaTicket ticket{handle, acl_epoch, service_generation_, ++request_id_};
    sessions_[handle] = Session{ticket, native_evidence};
    return ticket;
  }

  bool DescriptorValidated(JavaTicket ticket) {
    Session* s = Current(ticket);
    if (!s || s->uhid_created) return false;
    s->descriptor_validated = true;
    return true;
  }

  // Simulated asynchronous Java Handler reply. Java's standard policy must
  // still check quiet mode, bond state and connection policy independently.
  bool Reply(JavaTicket ticket, JavaVerdict result,
             bool java_quiet_mode, bool java_bonded,
             bool java_connection_policy_allowed) {
    Session* s = Current(ticket);
    if (!s || s->replied) return false;
    s->replied = true;
    if (result == JavaVerdict::kDeny) {
      sessions_.erase(ticket.handle);
      return true;
    }
    if (result == JavaVerdict::kCableReviewOnly) {
      s->cable_review_only = true;
      return true;  // NOT accepted; no bridge to a security exception
    }
    if (s->native_evidence != NativeEvidence::kVerifiedStandard ||
        java_quiet_mode || !java_bonded ||
        !java_connection_policy_allowed) {
      sessions_.erase(ticket.handle);
      return false;
    }
    s->java_standard_approved = true;
    return true;
  }

  bool ReleaseUhidCreate(JavaTicket ticket) {
    Session* s = Current(ticket);
    if (!s || s->uhid_created || !s->descriptor_validated ||
        !s->java_standard_approved ||
        s->native_evidence != NativeEvidence::kVerifiedStandard) return false;
    s->uhid_created = true;
    return true;
  }

  bool AllowInput(JavaTicket ticket, bool kernel_ready,
                  bool report_validated) {
    Session* s = Current(ticket);
    return s && s->uhid_created && s->java_standard_approved &&
           kernel_ready && report_validated;
  }

  bool Revoke(JavaTicket ticket) {
    if (!Current(ticket)) return false;
    sessions_.erase(ticket.handle);
    return true;
  }
  size_t Active() const { return sessions_.size(); }

 private:
  struct Session {
    JavaTicket ticket;
    NativeEvidence native_evidence;
    bool descriptor_validated = false;
    bool replied = false;
    bool java_standard_approved = false;
    bool cable_review_only = false;
    bool uhid_created = false;
  };
  Session* Current(JavaTicket t) {
    auto it = sessions_.find(t.handle);
    if (!active_ || it == sessions_.end() || !(it->second.ticket == t) ||
        t.service_generation != service_generation_) return nullptr;
    return &it->second;
  }
  uint64_t service_generation_ = 0;
  uint64_t request_id_ = 0;
  bool active_ = false;
  std::unordered_map<uint8_t, Session> sessions_;
};
}  // namespace retrobox
#endif  // RETROBOX_JAVA_ADMISSION_BRIDGE_H_
