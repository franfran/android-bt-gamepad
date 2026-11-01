// Host-only negative-completion ownership contract. No UHID writes/device access.
#pragma once
#include <cstdint>
#include <map>
#include <optional>
#include <set>
enum class FailureSite { Allocation, InvalidHandle, NoAcl, Congestion, SendError, RemoteNegative, Timeout, Disconnect };
struct NegativeReceipt { uint32_t request_id; FailureSite site; uint16_t handle; uint64_t generation; };
class NegativeCompletionModel {
 public:
  bool begin(uint16_t handle,uint64_t generation,uint32_t id) {
    if (closed_.count(handle) || pending_.count(handle)) return false;
    pending_[handle]={generation,id}; return true;
  }
  std::optional<NegativeReceipt> fail(uint16_t handle,uint64_t generation,FailureSite site) {
    auto it=pending_.find(handle);
    if(it==pending_.end() || it->second.generation!=generation || closed_.count(handle)) return std::nullopt;
    NegativeReceipt receipt{it->second.id,site,handle,generation};
    pending_.erase(it);
    closed_.insert(handle); // no reuse without externally proven isolation
    return receipt; // diagnostic ONLY; not a kernel reply
  }
  void disconnect(uint16_t handle) { pending_.erase(handle); closed_.insert(handle); }
  bool quarantined(uint16_t handle) const { return closed_.count(handle)>0; }
 private:
  struct Pending { uint64_t generation; uint32_t id; };
  std::map<uint16_t,Pending> pending_;
  std::set<uint16_t> closed_;
};
