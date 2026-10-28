# TV Box M3 — Hardware & Platform Inventory (Phase 2)

Source: user-collected `tvbox-m3-phase2.zip` plus previously reviewed Phase 1 inventory. Findings distinguish device-reported configuration from independently tested capabilities.

## Identity and operating system

| Field | Finding | Evidence / confidence |
|---|---|---|
| Model | M3 | Previously collected Android properties; reported, may be vendor-modified |
| Manufacturer | Oranth | Previously reported property |
| OS | Android TV 12 / API 31 | Phase 1 |
| Firmware | BigDroidOS 2.0.1, `apollo_p1-userdebug` | About screen / Phase 1 |
| Build date | 2024-04-12 | About screen |
| Kernel | Linux 5.4.125+, armv8l, Jan 8 2024 build | `soc.txt` |
| Root | `su` gives uid=0 | Confirmed interactively |
| SELinux | Permissive | Phase 1 |
| Security patch | 2022-02-05 | Phase 1 firmware report |

## SoC and CPU — identity conflict

- Device tree model: `sun50iw9`.
- Device tree compatible: `allwinner,h616` and `arm,sun50iw9p1`.
- `ro.hardware`: `sun50iw9p1`; `ro.board.platform`: `apollo`; `ro.boot.hardware`: `sun50iw9p1`.
- `ro.soc.model`: `H618`; `ro.soc.manufacturer`: `Allwinner`.
- **Conservative classification:** Allwinner H616/H618 family, firmware claims H618 while device-tree compatible string says H616. Exact silicon variant not independently validated.
- 4 × ARM Cortex-A53 (MIDR part 0xd03), ARMv8 hardware; running a 32-bit Android userspace (`armv8l`, previously reported `armeabi-v7a` application ABI).

## Memory / storage

- Phase 1 reported approximately 4 GB physical RAM and approximately 26 GB `/data` filesystem. These refer to different accounting measures than marketed storage capacity.

## Graphics and display

- GPU: ARM Mali-G31, driver GLES string `OpenGL ES 3.2 v1.r20p0-01rel0.9f6475d0baffb05079096179e1278b1d` (`surfaceflinger-full.txt`).
- Android-reported supported and current display mode: **1920 × 1080 at 60 Hz** (`display-full.txt`, `surfaceflinger-full.txt`). No other mode was enumerated in these dumps.
- `wm density`: 240; framebuffer modes file showed `U:1280x720p-0`, which is distinct from the current Android display mode and should not be interpreted as the HDMI maximum.
- HWC advertised HDR10=true, HLG=true, HDR10+=false, Dolby Vision=false; this is vendor/device report, not an actual HDR playback validation.
- HDMI 4K output **not proven**; `hdmi.txt` did not expose usable DRM connector modes.

## Vendor-declared MediaCodec capabilities

Source: `/vendor/etc/media_codecs.xml` (codec capability declarations), `/vendor/etc/media_codecs_performance.xml` (saved performance metadata). Values below are **declared**, not freshly benchmarked.

| Codec | Decoder | XML declared max frame size | XML 4096×2048 measured frame-rate range |
|---|---|---|---|
| AVC / H.264 | `OMX.allwinner.video.decoder.avc` | 4096×2176 | 15–35 fps |
| HEVC / H.265 | `OMX.allwinner.video.decoder.hevc` | 6144×3160 | 20–90 fps |
| VP9 | `OMX.allwinner.video.decoder.vp9` | 4096×2176 | 15–35 fps |
| VP8 | `OMX.allwinner.video.decoder.vp8` | 4096×2048 | not provided |
| MPEG-2 | `OMX.allwinner.video.decoder.mpeg2` | 1920×1080 | not provided |
| MPEG-4 | `OMX.allwinner.video.decoder.mpeg4` | 1920×1080 | not provided |
| MJPEG | `OMX.allwinner.video.decoder.mjpeg` | 1920×1080 | not provided |
| AV1 | none found among vendor codec declarations | unverified/not declared | not provided |

Further vendor codecs listed include MPEG-1, VP6, VC-1, DivX, Xvid, WMV1/WMV2 and other legacy formats. Secure decoder declarations exist for AVC, HEVC and VP9. Declared video hardware encoder: `OMX.allwinner.video.encoder.avc` with max 1280×720 (bitrate 1–20,000,000 bps); encoder performance XML also lists measurements at 1080p, so these declarations are internally inconsistent and should not be treated as proof of 1080p encoding capability.

Important caution: performance metadata provides historical/declarative ranges under specific conditions and cannot establish that the TV box will play particular 4K files smoothly. Profile/level, bitrate, thermal throttling and app/player behavior need separate verification.

## Capture integrity

- The Phase 2 ZIP contains the complete SoC/HDMI, codec XML, `media.player`, `media.metrics`, `display`, and `SurfaceFlinger` dumps plus error files. All listed `*-error.txt` files are empty.
- `media.metrics` contains runtime logs/metrics and is not a controlled benchmark.
- A missing `media.codec` dumpsys service in Phase 1 did not imply absence of codecs.

## Follow-up gaps (optional)

1. Determine exact silicon variant from board information / original manufacturer data rather than trusting one firmware field.
2. Confirm usable HDMI modes with a capable 4K television and actual display settings; current connected system reports only 1080p60.
3. Test actual 4K H.264/HEVC/VP9 decoding and codec profile support if required.
4. Verify thermal idle/load readings and throttling under controlled conditions.
5. Optionally inspect detailed audio codec/output declarations for a comparable cross-device inventory.
