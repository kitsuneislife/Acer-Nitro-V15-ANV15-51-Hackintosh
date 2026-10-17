# Bare metal research (Sequoia, no hardware swaps)

This research was done in October 2026, before choosing the VM route. It covers what a classic
OpenCore install on this laptop would mean.

> **Note (2026-10-16):** the project went bare metal after all. The display verdict below no longer holds: the RTX
> 3050 now composites the desktop with Metal and NMIntelFB shows it on the Intel panel (see the README and
> [nmx-intel](https://github.com/kitsuneislife/nmx-intel)). Wi-Fi is still unsolved.

**Verdict: not viable today.** Two parts this project can't do without, an accelerated internal
display and the internal Wi-Fi, both depend on unfinished projects that don't work on Sequoia.

## Compatibility matrix

| Component | Status | Solution / note |
|---|---|---|
| Hybrid CPU (4P+4E) | ✅ likely | `ProvideCurrentCpuInfo`, `CpuTopologyRebuild`, `SSDT-PLUG-ALT`. CFG Lock: `AppleXcpmCfgLock` quirk |
| Intel Xe iGPU (internal display) | ❌ on Sequoia | NootedGreen supports Sonoma 14.x only and is unfinished. Without it the panel runs on a framebuffer with no acceleration |
| RTX 3050 dGPU | ❌ for this laptop | The nullmoth driver needs a physical output on the NVIDIA card. With the panel on the Xe, Metal is unavailable (nvidia-macos-driver #106) |
| Wi-Fi MT7921 | ❌ | `SimpleMtkWlan`: scanning works, but connecting hangs or panics (#3). The developer has been inactive (#6) |
| Bluetooth MT7921 | ⚠️ likely | `SimpleMtkBtFw` matches `04CA:3802` exactly |
| Ethernet RTL8111 | ✅ | `RealtekRTL8111.kext` |
| Audio ALC245 | ⚠️ | AppleALC layouts 11, 12, 13. The SST DMIC (internal microphone) probably won't work |
| Touchpad PIXA3848 | ⚠️ likely | `VoodooI2C` + `VoodooI2CHID` + `SSDT-GPI0`. There are no reports for this exact PixArt part |
| Keyboard PS/2 | ✅ | `VoodooPS2Controller` |
| NVMe | ✅ likely | `NVMeFix` |
| Webcam UVC | ✅ likely | Native |
| Battery | ✅ likely | `ECEnabler` + `SMCBatteryManager` |
| Sleep / brightness | ❓ | Doubtful without an accelerated iGPU |

## Other blockers

- **The BIOS is locked down.** It's an Insyde BIOS with no Advanced menu, so CFG Lock and DVMT
  can't be changed without a BIOS mod. Resizable BAR is already on.
- **The boot may hang at `EXITBS:START`.** This was reported on two nearly identical laptops
  (nullmoth/1401 #26, nvidia-macos-driver #109). It may just be a missing display after the iGPU
  is disabled.
- **The NVIDIA driver is very young.** Reports include regressions between versions, panics and
  unreliable sleep.

## Fallback: Sonoma 14 with NootedGreen

This is the only way to try for an accelerated internal display. The author's main platform is
Raptor Lake-P (`0xBA`), the same CPU family as this laptop. The project still freezes WindowServer
and panics. It doesn't meet the Sequoia requirement, and the Wi-Fi still wouldn't work.

## Sources

- NootedGreen: https://github.com/sgiammori/NootedGreen
- SimpleMtkWlan: https://github.com/laobamac/SimpleMtkWlan (issues #3, #6)
- SimpleMtkBtFw: https://github.com/laobamac/SimpleMtkBtFw
- nvidia-macos-driver: https://github.com/nullmoth/nvidia-macos-driver (issues #104, #106, #109)
- nullmoth/1401 #26: https://github.com/nullmoth/1401/issues/26
- AppleALC codecs: https://github.com/acidanthera/AppleALC/wiki/Supported-codecs
- Dortania kernel issues: https://dortania.github.io/OpenCore-Install-Guide/troubleshooting/extended/kernel-issues.html
- Acer community, no MUX on the Nitro V 15: https://community.acer.com/en/discussion/726389/why-our-laptop-doesnt-havee-the-mux-switch-the-nitro-v15
