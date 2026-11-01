// Offline-only Linux v5.4 UHID SET_REPLY ABI model; NEVER writes /dev/uhid.
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <optional>
enum class ReceiptOrigin { KernelSet, Output, Hal };
struct SetReply { uint32_t id; uint16_t err; };
static_assert(sizeof(SetReply)==8, "host padded struct; do not memcpy directly as kernel ABI");
#pragma pack(push,1)
struct PackedSetReply { uint32_t id; uint16_t err; };
#pragma pack(pop)
static_assert(sizeof(PackedSetReply)==6, "Linux UHID packed response body must be 6 bytes");
struct Token { ReceiptOrigin origin; uint32_t id; uint64_t generation; };
std::optional<PackedSetReply> map_reply(Token token, uint64_t actual_generation,
                                       bool attribution_proven, bool completed,
                                       uint8_t native_status) {
  if (token.origin != ReceiptOrigin::KernelSet || token.generation != actual_generation ||
      !attribution_proven || !completed) return std::nullopt;
  // v5.4 uhid_hid_set_report evaluates err as boolean; no raw enum passthrough.
  return PackedSetReply{token.id, static_cast<uint16_t>(native_status == 0 ? 0 : 1)};
}
int main() {
  Token t{ReceiptOrigin::KernelSet,0xffffffffu,42};
  assert(!map_reply(t,42,false,true,0));
  assert(!map_reply(t,43,true,true,0));
  assert(!map_reply(t,42,true,false,0));
  auto positive=map_reply(t,42,true,true,0);
  assert(positive && positive->id==0xffffffffu && positive->err==0);
  auto negative=map_reply(t,42,true,true,7);
  assert(negative && negative->err==1);
  assert(!map_reply({ReceiptOrigin::Hal,5,42},42,true,true,0));
  assert(!map_reply({ReceiptOrigin::Output,5,42},42,true,true,0));
  std::cout<<"UHID v5.4 packed SET_REPLY host mapping PASS\n";
}
