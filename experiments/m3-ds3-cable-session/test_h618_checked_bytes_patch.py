#!/usr/bin/env python3
"""Host-compile the *exact added helper* from the pinned disabled H618 patch.

Uses fake JNI scheduler + allocation symbols; does NOT compile Android/H618.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
PATCH = ROOT / "h618_checked_bytes_disabled.patch"
text = PATCH.read_text()
assert "diff --git a/system/bt/btif/include/btif_common.h" in text
assert "diff --git a/system/bt/btif/src/btif_core.cc" in text
assert "system/bt/stack/btm/" not in text
assert "BTA_SEC_AUTHENTICATE" not in text
assert "BOND_BONDED" not in text
source = text.split("diff --git a/system/bt/btif/src/btif_core.cc", 1)[1]
additions = [line[1:] for line in source.splitlines()
             if line.startswith("+") and not line.startswith("+++")]
start = additions.index("#if defined(RETROBOX_DS3_PRIVATE_DESCRIPTOR_RESEARCH)")
end = additions.index("#endif", start)
helper = "\n".join(additions[start:end + 1])
assert "do_in_jni_thread(base::Bind(&bt_jni_msg_ready, p_msg))" in helper
assert "if (result != BT_STATUS_SUCCESS)" in helper
assert "osi_free(p_msg)" in helper
assert "memcpy(p_msg->p_param, bytes" in helper

shim = r"""
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <iostream>
#include <string>
#include <vector>

using bt_status_t = int;
constexpr bt_status_t BT_STATUS_SUCCESS = 0;
constexpr bt_status_t BT_STATUS_FAIL = 1;
constexpr unsigned BT_EVT_CONTEXT_SWITCH_EVT = 42;
using tBTIF_CBACK = void(uint16_t, char*);
struct BT_HDR_RIGID { unsigned event; };
struct tBTIF_CONTEXT_SWITCH_CBACK {
  BT_HDR_RIGID hdr;
  tBTIF_CBACK* p_cb;
  uint16_t event;
  char p_param[1]; // shim-only: real H618 is a flexible array
};
static size_t allocs = 0, frees = 0;
static bool scheduler_accepts = true;
static std::vector<std::function<void()>> pending;
static std::string last_payload;
static uint16_t last_event = 0;
static size_t expected_bytes = 0;
void* osi_malloc(size_t n) { ++allocs; return std::malloc(n); }
void osi_free(void* p) { ++frees; std::free(p); }
static void bt_jni_msg_ready(void* raw) {
  auto* msg = static_cast<tBTIF_CONTEXT_SWITCH_CBACK*>(raw);
  if (msg->p_cb) msg->p_cb(msg->event, msg->p_param);
  osi_free(msg);
}
namespace base {
template<class P> std::function<void()> Bind(void (*fn)(void*), P* ptr) {
  return [=] { fn(static_cast<void*>(ptr)); };
}
}
bt_status_t do_in_jni_thread(std::function<void()> task) {
  if (!scheduler_accepts) return BT_STATUS_FAIL;
  pending.push_back(std::move(task));
  return BT_STATUS_SUCCESS;
}
static void inspect(uint16_t evt, char* bytes) {
  last_event = evt;
  last_payload.assign(bytes, expected_bytes);
}
static bool Check(bool value, const char* msg) {
  if (!value) { std::cerr << "FAIL " << msg << "\n"; return false; }
  return true;
}
#define RETROBOX_DS3_PRIVATE_DESCRIPTOR_RESEARCH
"""
tail = r"""
int main() {
  size_t passed = 0;
  auto tick = [&](bool ok, const char* msg) {
    if (!Check(ok, msg)) std::exit(1);
    ++passed;
  };
  char payload[] = {1, 2, 3};
  tick(btif_transfer_context_checked_bytes(nullptr, 9, payload, 3) ==
       BT_STATUS_FAIL, "null callback");
  tick(btif_transfer_context_checked_bytes(&inspect, 9, nullptr, 3) ==
       BT_STATUS_FAIL, "null data");
  tick(btif_transfer_context_checked_bytes(&inspect, 9, payload, 0) ==
       BT_STATUS_FAIL, "zero length");
  tick(btif_transfer_context_checked_bytes(&inspect, 9, payload, -1) ==
       BT_STATUS_FAIL, "negative length");
  tick(btif_transfer_context_checked_bytes(&inspect, 9, payload, 4113) ==
       BT_STATUS_FAIL, "oversized fixture");
  tick(allocs == 0 && frees == 0, "invalid inputs allocate nothing");
  scheduler_accepts = false;
  tick(btif_transfer_context_checked_bytes(&inspect, 9, payload, 3) ==
       BT_STATUS_FAIL, "scheduler rejection propagated");
  tick(allocs == 1 && frees == 1 && pending.empty(), "post failure freed");
  scheduler_accepts = true;
  expected_bytes = 3;
  tick(btif_transfer_context_checked_bytes(&inspect, 9, payload, 3) ==
       BT_STATUS_SUCCESS, "scheduler accepted");
  tick(allocs == 2 && frees == 1 && pending.size() == 1, "task held until run");
  payload[0] = 9;
  pending.front()();
  pending.clear();
  tick(last_event == 9 && last_payload == std::string("\1\2\3", 3),
       "copied bytes independent from producer");
  tick(allocs == frees && pending.empty(), "callback released exactly once");
  std::cout << passed << "/" << passed
            << " PASS (patched helper compiled with mock JNI symbols)\n";
}
"""
with tempfile.TemporaryDirectory() as tmp:
    source_file = Path(tmp) / "patched_helper_test.cc"
    binary_file = Path(tmp) / "patched_helper_test"
    source_file.write_text(shim + "\n" + helper + "\n" + tail)
    cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
           "-pedantic", "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
           str(source_file), "-o", str(binary_file)]
    subprocess.run(cmd, check=True)
    subprocess.run([str(binary_file)], check=True)
