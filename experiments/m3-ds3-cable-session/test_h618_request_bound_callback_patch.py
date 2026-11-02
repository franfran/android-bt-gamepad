#!/usr/bin/env python3
"""Compile the actual added H618 callback wrapper against mocked ACL/BTM types.

The source is extracted from the committed *overlay* patch, not reimplemented.
Does NOT compile Android, authenticate DS3, or enable any source feature flag.
"""
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
patch = (HERE / "h618_request_bound_btm_callback_disabled.patch").read_text()
section = patch.split(
    "diff --git a/system/bt/stack/l2cap/l2c_link.cc", 1
)[1].split("diff --git ", 1)[0]
added = [line[1:] for line in section.splitlines()
         if line.startswith("+") and not line.startswith("+++")]
first = added.index("namespace {") - 2
assert added[first].startswith("#if defined(RETROBOX_DS3_REQUEST_REF_OBSERVE)")
last = added.index("#endif", first)
source_block = "\n".join(added[first:last + 1])
assert "retrobox_btm_request_ref_callback" in source_block
assert "l2c_link_sec_comp2(*bda, transport, match, status)" in source_block
assert "g_retrobox_request_refs.PendingIdentity(ref)" in source_block

mock_prefix = r"""
#include "request_refs.h"
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>
struct RawAddress { int value; };
enum tBT_TRANSPORT { BT_TRANSPORT_BR_EDR=1, BT_TRANSPORT_LE=2 };
using tBTM_STATUS = int;
constexpr int BTM_DELAY_CHECK=100, BTM_SUCCESS=0, BTM_SUCCESS_NO_SECURITY=1;
constexpr int BTM_ERR_PROCESSING=20;
struct tL2C_CCB;
struct Rcb { uint16_t psm; };
struct Queue { tL2C_CCB* p_first_ccb; };
struct tL2C_LCB {
  tBT_TRANSPORT transport;
  uint16_t handle;
  RawAddress addr;
  Queue ccb_queue;
  uint16_t Handle() const { return handle; }
};
struct tL2C_CCB {
  tL2C_LCB* p_lcb;
  Rcb* p_rcb;
  tL2C_CCB* p_next_ccb;
};
static tL2C_LCB* live_link = nullptr;
static uint64_t live_epoch = 0;
static std::vector<int> forwarded;
uint64_t retrobox_acl_epoch_for_lcb(const tL2C_LCB* lcb) {
  return lcb==live_link ? live_epoch : 0;
}
tL2C_LCB* l2cu_find_lcb_by_bd_addr(const RawAddress& bda,
                                  tBT_TRANSPORT transport) {
  return live_link && live_link->addr.value == bda.value &&
                 live_link->transport == transport ? live_link : nullptr;
}
void l2c_link_sec_comp2(const RawAddress&, tBT_TRANSPORT,
                        void*, tBTM_STATUS status) {
  forwarded.push_back(status);
}
#define RETROBOX_DS3_REQUEST_REF_OBSERVE
#define RETROBOX_DS3_ACL_EPOCH_OBSERVE
"""

mock_tests = r"""
void Check(bool ok) {
  if (!ok) throw std::runtime_error("mock callback invariant failed");
}
int main() {
  Rcb control{0x11}, interrupt{0x13}, unrelated{0x17};
  tL2C_LCB lcb{BT_TRANSPORT_BR_EDR,7,{11},{nullptr}};
  tL2C_CCB ccb{&lcb,&control,nullptr};
  lcb.ccb_queue.p_first_ccb=&ccb;
  live_link=&lcb;live_epoch=1;
  int checks=0;
  auto check=[&](bool ok){Check(ok);++checks;};
  auto first=retrobox_begin_btm_request_ref(&ccb);
  check(first!=nullptr);
  retrobox_btm_request_ref_callback(&lcb.addr,BT_TRANSPORT_BR_EDR,first,
                                   BTM_SUCCESS);
  check(forwarded.size()==1&&forwarded.back()==BTM_SUCCESS);
  retrobox_btm_request_ref_callback(&lcb.addr,BT_TRANSPORT_BR_EDR,first,
                                   BTM_SUCCESS);
  check(forwarded.size()==1);
  auto delayed=retrobox_begin_btm_request_ref(&ccb);
  check(delayed!=nullptr);
  retrobox_btm_request_ref_callback(&lcb.addr,BT_TRANSPORT_BR_EDR,delayed,
                                   BTM_DELAY_CHECK);
  check(forwarded.size()==2&&forwarded.back()==BTM_DELAY_CHECK);
  retrobox_btm_request_ref_callback(&lcb.addr,BT_TRANSPORT_BR_EDR,delayed,
                                   BTM_ERR_PROCESSING);
  check(forwarded.size()==3&&forwarded.back()==BTM_ERR_PROCESSING);
  auto stale=retrobox_begin_btm_request_ref(&ccb);
  check(stale!=nullptr);
  live_epoch=2;
  retrobox_btm_request_ref_callback(&lcb.addr,BT_TRANSPORT_BR_EDR,stale,
                                   BTM_SUCCESS);
  check(forwarded.size()==3);
  auto current=retrobox_begin_btm_request_ref(&ccb);
  check(current!=nullptr);
  retrobox_retire_refs_for_ccb(&ccb);
  retrobox_btm_request_ref_callback(&lcb.addr,BT_TRANSPORT_BR_EDR,current,
                                   BTM_SUCCESS);
  check(forwarded.size()==3);
  auto to_retire=retrobox_begin_btm_request_ref(&ccb);
  check(to_retire!=nullptr);
  retrobox_retire_refs_for_lcb(&lcb);
  retrobox_btm_request_ref_callback(&lcb.addr,BT_TRANSPORT_BR_EDR,to_retire,
                                   BTM_SUCCESS);
  check(forwarded.size()==3);
  ccb.p_rcb=&unrelated;
  check(!retrobox_begin_btm_request_ref(&ccb));
  ccb.p_rcb=&interrupt;
  auto intr=retrobox_begin_btm_request_ref(&ccb);
  check(intr!=nullptr);
  live_epoch=3;
  retrobox_btm_request_ref_callback(&lcb.addr,BT_TRANSPORT_BR_EDR,intr,
                                   BTM_SUCCESS);
  check(forwarded.size()==3);
  auto now=retrobox_begin_btm_request_ref(&ccb);
  RawAddress wrong{99};
  retrobox_btm_request_ref_callback(&wrong,BT_TRANSPORT_BR_EDR,now,
                                   BTM_SUCCESS);
  check(forwarded.size()==3);
  check(g_retrobox_request_refs.Issued()>0);
  std::cout<<checks<<"/"<<checks<<" PASS (source-extracted BTM callback)\\n";
}
"""

with tempfile.TemporaryDirectory() as temp:
    src = Path(temp) / "callback.cc"
    src.write_text(mock_prefix + "\n" + source_block + "\n" + mock_tests)
    for sanitized in (False, True):
        binary = Path(temp) / ("callback_asan" if sanitized else "callback")
        command = [
            "g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic",
            "-I", str(HERE),
        ]
        if sanitized:
            command += ["-fsanitize=address,undefined",
                        "-fno-omit-frame-pointer"]
        command += [str(src), "-o", str(binary)]
        subprocess.run(command, check=True)
        subprocess.run([str(binary)], check=True)
