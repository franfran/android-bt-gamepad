# TV Box Hardware Profile — M3 / BigDroidOS 2.0.1

**Collection date:** 2026-10-24  
**Source:** user-collected ADB reports `imex` and `tvbox-m3-report.zip`  
**Scope:** Hardware and platform inventory (not subtitle-project implementation)

## Identity & operating system

| Attribute | Value | Evidence / confidence |
|---|---|---|
| Model / manufacturer | M3 / Oranth | `ro.product.model`, `ro.product.manufacturer` (reported) |
| OS | Android 12, API 31 | `ro.build.version.*` |
| UI | BigDroidOS 2.0.1 | On-device About screen, user observed |
| Build | `SP1A.211105.004`, incremental `20240412.161509` | `getprop` |
| Build type | `userdebug` | `getprop` |
| Security patch | 2022-02-05 | `getprop`; reported level is not an independent security audit |
| Board / platform | `apollo` / `sun50iw9p1` | `ro.board.platform`, `ro.hardware` |
| SoC family | Possibly Allwinner H618 | Inferential; OTA endpoint refers to H618, confirm with device tree |
| Build fingerprint | `google/raven/raven:12/...` | Reported, apparently vendor-customized; not reliable identification of Google hardware |
| CPU | 4 × Cortex-A53 | Earlier `/proc/cpuinfo` report |
| Android ABI | `armeabi-v7a,armeabi` (no 64-bit ABI exposed) | `ro.product.cpu.abilist*` |
| RAM | 4 GiB class | Earlier `/proc/meminfo`; `ro.boot.dramsize=4096` |
| Data volume | ~26 GB | Earlier `df -h`; not necessarily total flash capacity |
| Linux kernel | 5.4.125+ | Earlier `/proc/version` report |

## Graphics and display

| Attribute | Evidence / result |
|---|---|
| GPU | ARM Mali-G31, direct `dumpsys SurfaceFlinger` GLES identification |
| OpenGL ES | 3.2, driver version `v1.r20p0-01rel0` |
| Current display mode | 1920 × 1080, 60 Hz |
| Android HDR reporting | Supported HDR type IDs [2,3] (HDR10, HLG); this is advertised capability, not verified playback |
| Vulkan | Not established by this report |
| Max hardware HDMI resolution | Not established; current mode is 1080p60 |

## Media codecs

These are **registered Android MediaCodec implementations**, not playback benchmarks:

| Codec | Vendor decoder registered |
|---|---|
| AVC / H.264 | `OMX.allwinner.video.decoder.avc`, and secure variant |
| HEVC / H.265 | `OMX.allwinner.video.decoder.hevc`, and secure variant |
| VP9 | `OMX.allwinner.video.decoder.vp9`, and secure variant |
| VP8 | `OMX.allwinner.video.decoder.vp8` |
| MPEG-2 | `OMX.allwinner.video.decoder.mpeg2` |
| MPEG-4 | `OMX.allwinner.video.decoder.mpeg4` |
| AV1 | No decoder enumerated in collected list |
| H.264 encoder | `OMX.allwinner.video.encoder.avc` |

`dumpsys media.codec` returns `Can't find service: media.codec`; `dumpsys media.player` does enumerate codecs. XML available at `/vendor/etc/media_codecs.xml` and `/vendor/etc/media_codecs_performance.xml`, not yet extracted.

## Audio and connectivity

- HDMI audio presence indicated by property `audio.hdmi.available=1` and HDMI entries in Android audio routing.
- HDMI CEC playback client and CEC volume control reported.
- Actual supported HDMI audio formats, passthrough and sample rates not tested.
- Network ADB connection established over LAN; avoid leaving it enabled outside debugging sessions.

## Security / trust caveats

- Root shell confirmed from local terminal: `uid=0(root)`.
- SELinux reported permissive.
- Bootloader state reported locked; root availability does **not** imply an unlocked bootloader.
- `ro.boot.veritymode=enforcing` is separately reported; do not infer full verified-boot integrity from properties alone.
- Security patch property is dated February 2022; vendor build dated April 2024.
- Reported `google/raven` product fingerprint conflicts with Allwinner hardware identifiers, illustrating why firmware identity fields should not be treated as physical model authentication.

## Outstanding follow-up checks

1. Read device-tree model / compatible (`/proc/device-tree/model`, `/proc/device-tree/compatible`) to confirm precise SoC/board.
2. Retrieve vendor codec XML to assess declared size/rate/profile limits.
3. Query display connector modes / EDID if available; current 1080p60 does not establish max resolution.
4. Run a small non-invasive temperature sample after idle vs playback; prior readings were near 78–81°C, interpretation requires workload and sensors validation.
5. Identify Wi-Fi/Bluetooth chip, flash/eMMC capacity and filesystem if cross-device comparisons require these.

## Recommended read-only next probe (Mac)

```sh
DEVICE=192.0.2.10:5555
mkdir -p m3-followup
adb -s "$DEVICE" shell 'cat /proc/device-tree/model 2>/dev/null; echo' > m3-followup/device-tree-model.txt
adb -s "$DEVICE" shell 'tr "\000" "\n" < /proc/device-tree/compatible 2>/dev/null' > m3-followup/device-tree-compatible.txt
adb -s "$DEVICE" shell cat /vendor/etc/media_codecs.xml > m3-followup/media_codecs.xml
adb -s "$DEVICE" shell cat /vendor/etc/media_codecs_performance.xml > m3-followup/media_codecs_performance.xml
adb -s "$DEVICE" shell 'ls -l /sys/class/drm /sys/block 2>/dev/null' > m3-followup/devices.txt
zip -r m3-followup.zip m3-followup
```

**Privacy:** Raw system properties may contain unique device serials or network identifiers; do not publicly post entire raw dumps without redaction.
