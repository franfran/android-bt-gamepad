#!/usr/bin/env python3
"""Compile source-extracted passive BTM/L2CAP observation blocks with mock types.

No Android build, device I/O, credentials, controller identity or pairing changes.
"""
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
patch = (HERE / "h618_btm_hid_auth_observe_disabled.patch").read_text()
FLAG = "RETROBOX_DS3_BTM_AUTH_OBSERVE"


def added_block(path):
    section = patch.split(f"diff --git a/{path} b/{path}", 1)[1].split(
        "diff --git ", 1
    )[0]
    lines = [line[1:] for line in section.splitlines()
             if line.startswith("+") and not line.startswith("+++")]
    assert lines[0] == f"#if defined({FLAG})"
    assert lines[-1] == "#endif"
    return "\n".join(lines)


btm = added_block("system/bt/stack/btm/btm_sec.cc")
l2cap = added_block("system/bt/stack/l2cap/l2c_link.cc")
assert "!is_originator" in btm
assert "security_required" in btm
assert "p_ccb->p_rcb != nullptr" in l2cap
assert "BTM_status=" in l2cap
assert "btm_sec_l2cap_access_req_by_requirement" in patch
assert "switch (status)" in patch
assert "BTA_SEC_AUTHENTICATE" not in patch
assert "BOND_BONDED" not in patch
assert "HCI_PIN_TYPE" not in patch
assert not any(line.startswith("-") and not line.startswith("---")
               for line in patch.splitlines())

prefix = r'''
#include <cstdint>
#include <cstdarg>
#include <cstdio>
#include <string>
#include <vector>
#include <stdexcept>
#include <iostream>
struct Rcb { uint16_t psm; };
struct Ccb { Rcb* p_rcb; };
struct BtmCb { unsigned security_mode = 2; } btm_cb;
static std::vector<std::string> logs;
void capture_log(const char* fmt, ...) {
  char buf[256];
  va_list args; va_start(args, fmt);
  std::vsnprintf(buf, sizeof(buf), fmt, args);
  va_end(args);
  logs.emplace_back(buf);
}
#define LOG_INFO(...) capture_log(__VA_ARGS__)
void btm_observe(uint16_t psm, bool is_originator, uint16_t security_required) {
  (void)psm; (void)is_originator; (void)security_required;
'''
middle = r'''
}
void l2cap_observe(Ccb* p_ccb, int status) {
  (void)p_ccb; (void)status;
'''
suffix = r'''
}
void expect(bool condition, const char* description) {
  if (!condition) throw std::runtime_error(description);
}
int main() {
#ifdef RETROBOX_DS3_BTM_AUTH_OBSERVE
  btm_observe(0x11, false, 0x140);
  expect(logs.size() == 1 && logs.back().find("PSM=0x0011") != std::string::npos,
    "inbound control request observed");
  btm_observe(0x13, false, 0x140);
  expect(logs.size() == 2 && logs.back().find("PSM=0x0013") != std::string::npos,
    "inbound interrupt request observed");
  btm_observe(0x11, true, 0x140);
  expect(logs.size() == 2, "outbound request not observed");
  btm_observe(0x17, false, 0x140);
  expect(logs.size() == 2, "unrelated PSM not observed");
  Rcb control{0x11}, interrupt{0x13}, unrelated{0x17};
  Ccb c1{&control}, c2{&interrupt}, c3{&unrelated}, empty{nullptr};
  l2cap_observe(&c1, 0);
  expect(logs.size() == 3 && logs.back().find("BTM_status=0") != std::string::npos,
    "control success callback");
  l2cap_observe(&c2, 42);
  expect(logs.size() == 4 && logs.back().find("BTM_status=42") != std::string::npos,
    "interrupt failure callback");
  l2cap_observe(&c3, 0);
  expect(logs.size() == 4, "unrelated CCB ignored");
  l2cap_observe(&empty, 0);
  expect(logs.size() == 4, "missing RCB ignored");
  for (const auto& item : logs) {
    expect(item.find("MAC") == std::string::npos, "no peer address");
    expect(item.find("PIN") == std::string::npos, "no PIN value");
  }
  std::cout << "16/16 PASS (feature on; mock types, observer only)\n";
#else
  Rcb control{0x11}; Ccb c1{&control};
  btm_observe(0x11, false, 0x140);
  l2cap_observe(&c1, 42);
  expect(logs.empty(), "flag disabled means no logging");
  std::cout << "1/1 PASS (feature off; no observer logging)\n";
#endif
}
'''
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    source = base / "probe_test.cc"
    source.write_text(prefix + btm + middle + l2cap + suffix)
    for enabled in (False, True):
        binary = base / ("observer_on" if enabled else "observer_off")
        command = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic",
                   "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
        if enabled:
            command.append(f"-D{FLAG}")
        command += [str(source), "-o", str(binary)]
        subprocess.run(command, check=True)
        subprocess.run([str(binary)], check=True)
