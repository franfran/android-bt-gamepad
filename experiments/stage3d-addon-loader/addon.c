/* Stage 3D D1: inert, freestanding ARM32 dlopen target; no Android/Bluetooth APIs. */
__attribute__((visibility("default")))
unsigned retrobox_addon_abi(void) { return 0x00030001u; }
__attribute__((visibility("default")))
unsigned retrobox_addon_probe(unsigned nonce) { return nonce ^ 0x52425833u; }
