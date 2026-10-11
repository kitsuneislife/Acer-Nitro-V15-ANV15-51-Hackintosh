# Acer Nitro V 15 (ANV15-51): macOS 15 Sequoia

This repo is about running macOS 15 Sequoia on the Acer Nitro V 15 ANV15-51. The goal is to use the
laptop's own display and Wi-Fi, with no hardware swaps.

> **Status: work in progress. None of this has been tested yet.**
> A row in the [status table](#status) changes only after a successful test, and every changed
> row links to its proof: a screenshot, a log, or the exact command.

## Approach: a VM, not bare metal

With bare metal, Sequoia can't meet the two main requirements on this laptop (details in
[docs/bare-metal.md](docs/bare-metal.md)):

- **Internal display.** The panel is wired to the Intel Xe iGPU, and the laptop has no MUX. The
  only Xe acceleration project, NootedGreen, runs only on Sonoma and is still unfinished. The RTX
  3050 can't drive the panel at all. The community NVIDIA driver also has no Metal when the card
  has no display attached.
- **Internal Wi-Fi.** The card is a MediaTek MT7921, and its only driver is SimpleMtkWlan. With
  that driver the card can scan, but connecting to a network hangs or panics.

So macOS runs as a **QEMU/KVM guest on a Linux host**. Linux drives the panel and the Wi-Fi. The
guest sees a virtual display and a virtual Ethernet card, so it needs no Wi-Fi or GPU kexts.

1. **Base:** [OSX-KVM](https://github.com/kholia/OSX-KVM) (OpenCore + OVMF), without graphics
   acceleration.
2. **Metal:** [Reims vGPU](https://github.com/steelbrain/reims-vgpu), a paravirtualized GPU. The
   guest uses Apple's stock `AppleParavirtGPU.kext`, and the host runs Metal on top of Vulkan.
   Reims is alpha software.

## Hardware

| Component | Model | IDs |
|---|---|---|
| CPU | Intel Core i5-13420H (Raptor Lake-H, 4P+4E, 12 threads) | CPUID family 6 model `0xBA` |
| iGPU | Intel UHD Graphics (Xe-LP) | `8086:A7A8` |
| dGPU | NVIDIA GeForce RTX 3050 6GB Laptop (GA107) | `10DE:25AC` |
| Display | LG Display `LGD0742`, eDP 144 Hz, on the iGPU (no MUX) | |
| RAM | 16 GB | |
| SSD | NVMe SM2P41C8-512GC5 | |
| Wi-Fi / BT | MediaTek MT7921 | `14C3:7961`, USB `04CA:3802` |
| Ethernet | Realtek RTL8168/8111 | `10EC:8168` |
| Audio | Realtek ALC245 via Intel SST | `10EC:0245` |
| Touchpad | PixArt PIXA3848, I2C HID | |
| BIOS | Insyde V1.60, no Advanced menu | |

## Host

The host runs CachyOS (Arch-based) with kernel 7.2.9, QEMU 11.1.2, the NVIDIA open driver
615.78.08 and Mesa 26.2.4. KVM is loaded with `ignore_msrs=1`. The guest is pinned to the P-cores
(CPUs 0-7), with 4 cores, 8 threads and 8 GiB of RAM.

## Status

Legend: ✅ works, ⚠️ partial, ❌ broken, ⏳ not tested yet.

| Feature | Status | Notes / proof |
|---|---|---|
| Sequoia 15.8.1 (24H32) install, offline from Apple's InstallAssistant.pkg | ⏳ | |
| Boot to desktop | ⏳ | |
| Internal display (window / full screen) | ⏳ | |
| Network through host Wi-Fi | ⏳ | |
| Keyboard and touchpad (through host) | ⏳ | |
| Audio | ⏳ | |
| Metal (Reims vGPU) | ⏳ | |
| Daily use without hangs | ⏳ | |

## Roadmap

- [ ] Phase 2: Sequoia base install with OSX-KVM (no acceleration)
- [ ] Phase 3: Reims vGPU (Metal), tested with both the Intel ANV and NVIDIA Vulkan drivers on the host
- [ ] Phase 4: daily use (full screen, audio, shared folder, backups)

The QEMU launch scripts and the OpenCore config will be added here once the matching phase is
verified.

## What this repo doesn't include

- **No Apple software.** Download macOS from Apple yourself, for example with OSX-KVM's
  `fetch-macOS-v2.py`.
- **No SMBIOS identifiers.** Any `config.plist` here has its serial, MLB, ROM and SystemUUID
  blanked out, so generate your own.

## Credits

- [OSX-KVM](https://github.com/kholia/OSX-KVM)
- [OpenCore](https://github.com/acidanthera/OpenCorePkg) and acidanthera
- [Reims vGPU](https://github.com/steelbrain/reims-vgpu)
- [Dortania guides](https://dortania.github.io/)

## Disclaimer

Apple's license may not allow running macOS on non-Apple hardware. This repo is for research and
education only, and you use it at your own risk.
