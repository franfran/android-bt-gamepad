#!/usr/bin/env python3
"""Compile the EXACT added BTIF probe extracted from the H618 source patch.

Only a stand-in scheduler and C++17 host environment are used. No Android build,
Bluetooth operations, actual DS3 descriptor, or real authorization is performed.
"""
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
patch = (HERE / "h618_private_descriptor_probe_disabled.patch").read_text()
btif = patch.split("diff --git a/system/bt/btif/src/btif_hh.cc", 1)[1]
added = [line[1:] for line in btif.splitlines()
         if line.startswith("+") and not line.startswith("+++")]
assert added[0] == "#if defined(RETROBOX_DS3_PRIVATE_DESCRIPTOR_RESEARCH)"
assert added[-1] == "#endif"
code = "\n".join(added)
bta = patch.split("diff --git a/system/bt/bta/hh/bta_hh_act.cc", 1)[1].split(
    "diff --git a/system/bt/btif/src/btif_hh.cc", 1)[0]
assert "!p_cb->is_le_device" in bta
assert "btif_hh_ds3_probe_descriptor(" in bta
assert "(*bta_hh_cb.p_cback)(BTA_HH_GET_DSCP_EVT" in bta
assert "BTA_SEC_AUTHENTICATE" not in patch
assert "BOND_BONDED" not in patch
assert "UHID_CREATE" not in patch

shim = r"""
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <vector>
#include <iostream>
#include <cstdlib>
using bt_status_t = int;
constexpr bt_status_t BT_STATUS_SUCCESS = 0;
constexpr bt_status_t BT_STATUS_FAIL = 1;
using tBTIF_CBACK = void(uint16_t, char*);
static bool scheduler_accepts = true;
static size_t attempts = 0;
static std::vector<char> scheduled;
static tBTIF_CBACK* handler = nullptr;
static uint16_t scheduled_event = 0;
bt_status_t btif_transfer_context_checked_bytes(tBTIF_CBACK* cb,
  uint16_t event, const char* bytes, int size) {
  ++attempts;
  if (!scheduler_accepts) return BT_STATUS_FAIL;
  handler = cb; scheduled_event = event;
  scheduled.assign(bytes, bytes + size);
  return BT_STATUS_SUCCESS;
}
#define BTIF_TRACE_DEBUG(...) do {} while (0)
#define BTIF_TRACE_WARNING(...) do {} while (0)
#define RETROBOX_DS3_PRIVATE_DESCRIPTOR_RESEARCH
"""
tests = r"""
int main() {
  size_t passed = 0;
  auto check = [&](bool ok) {
    if (!ok) std::exit(1);
    ++passed;
  };
  uint8_t bytes[] = {1, 2, 3};
  btif_hh_ds3_probe_descriptor(4, 0x054c, 0x0268, nullptr, 3);
  check(attempts == 0);
  btif_hh_ds3_probe_descriptor(4, 0x054c, 0x0268, bytes, 0);
  check(attempts == 0);
  btif_hh_ds3_probe_descriptor(4, 0x054c, 0x0268, bytes, 4097);
  check(attempts == 0);
  scheduler_accepts = false;
  btif_hh_ds3_probe_descriptor(4, 0x054c, 0x0268, bytes, 3);
  check(attempts == 1 && scheduled.empty());
  scheduler_accepts = true;
  btif_hh_ds3_probe_descriptor(4, 0x054c, 0x0268, bytes, 3);
  check(attempts == 2 && scheduled.size() == 4104);
  RetroboxProbe parsed{};
  std::memcpy(&parsed, scheduled.data(), sizeof(parsed));
  check(parsed.handle == 4 && parsed.vendor_id == 0x054c &&
        parsed.product_id == 0x0268 && parsed.length == 3);
  bytes[0] = 9;
  check(parsed.bytes[0] == 1 && scheduled_event == kRetroboxProbeEvent);
  check(handler != nullptr);
  handler(scheduled_event, scheduled.data());
  check(attempts == 2);
  // Mutating event's embedded length is ignored by the read-only consumer.
  parsed.length = 4097;
  std::memcpy(scheduled.data(), &parsed, sizeof(parsed));
  handler(scheduled_event, scheduled.data());
  check(attempts == 2);
  std::cout << passed << "/" << passed
    << " PASS (source-extracted BTA-to-BTIF passive probe; host mock)\n";
}
"""
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    src = path / "probe_test.cc"
    binary = path / "probe_test"
    src.write_text(shim + "\n" + code + "\n" + tests)
    command = [
        "g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
        str(src), "-o", str(binary),
    ]
    subprocess.run(command, check=True)
    subprocess.run([str(binary)], check=True)
