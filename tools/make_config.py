#!/usr/bin/env python3
"""Generate EFI/OC/config.plist for the Acer Nitro V 15 ANV15-51 from OpenCore's Sample.plist.

Every value that differs from Sample.plist is set here, with the reason next to it, so the config
can be reviewed as code and regenerated for each OpenCore release.

Usage: make_config.py SAMPLE_PLIST EFI_DIR [--smbios FILE] [--stage installer|installed]

EFI_DIR is the assembled EFI folder (it must already hold OC/ACPI, OC/Kexts and OC/Drivers);
the kext entries are read from the bundles found there. --smbios takes a JSON file with
SystemProductName, SystemSerialNumber, MLB, SystemUUID and ROM (hex). Without it the identifiers
stay blank, which is what the public repo ships.
"""
import argparse
import json
import plistlib
import sys
from pathlib import Path

APPLE_BOOT = "7C436110-AB2A-4BBB-A880-FE41995C9F82"
APPLE_VENDOR = "4D1FDA02-38C7-4A6A-9CC6-4BCCA8B30102"

SMBIOS_MODEL = "MacBookPro16,1"  # laptop Mac with a discrete GPU that runs macOS 15

# Injection order matters: a kext must come after every bundle it links against.
# (bundle path inside OC/Kexts, enabled, comment)
KEXTS = [
    ("Lilu.kext", True, "patching framework, needed by most kexts below"),
    ("VirtualSMC.kext", True, "SMC emulation"),
    ("SMCProcessor.kext", True, "CPU temperature sensors"),
    ("SMCBatteryManager.kext", True, "battery status"),
    ("ECEnabler.kext", True, "lets SMCBatteryManager read 16-bit EC fields"),
    ("AppleALC.kext", True, "ALC245 audio, layout set by alcid"),
    ("RestrictEvents.kext", True, "sbvmm for updates with SecureBootModel Disabled, CPU name"),
    ("NVMeFix.kext", True, "NVMe power management"),
    ("CpuTopologyRebuild.kext", False, "hybrid CPU scheduling; off until the base boots, then tested on its own"),
    ("VoodooPS2Controller.kext", True, "PS/2 keyboard"),
    ("VoodooPS2Controller.kext/Contents/PlugIns/VoodooPS2Keyboard.kext", True, "PS/2 keyboard"),
    ("VoodooPS2Controller.kext/Contents/PlugIns/VoodooPS2Mouse.kext", False, "touchpad is I2C, not PS/2"),
    ("VoodooPS2Controller.kext/Contents/PlugIns/VoodooPS2Trackpad.kext", False, "touchpad is I2C, not PS/2"),
    ("VoodooPS2Controller.kext/Contents/PlugIns/VoodooInput.kext", False, "VoodooI2C ships its own VoodooInput"),
    ("VoodooI2C.kext/Contents/PlugIns/VoodooGPIO.kext", True, "GPIO interrupts for the touchpad (INTC1055)"),
    ("VoodooI2C.kext/Contents/PlugIns/VoodooI2CServices.kext", True, "VoodooI2C dependency"),
    ("VoodooI2C.kext/Contents/PlugIns/VoodooInput.kext", True, "multitouch for the I2C touchpad"),
    ("VoodooI2C.kext", True, "I2C controller 8086:51E8 (match added by build.sh)"),
    ("VoodooI2CHID.kext", True, "PIXA3848 HID-over-I2C touchpad"),
    ("RealtekRTL8111.kext", True, "Ethernet RTL8111"),
    ("BrightnessKeys.kext", True, "brightness hotkeys"),
    ("SimpleMtkBtFw.kext", True, "MT7921 Bluetooth firmware loader (USB 04CA:3802)"),
    ("SimpleMtkBtPatcher.kext", True, "MT7921 Bluetooth compatibility patches"),
]

BOOT_ARGS = [
    "-v",                    # verbose boot while the EFI is being validated
    "keepsyms=1",            # symbols in panic logs
    "debug=0x100",           # stay on the panic screen instead of rebooting
    "alcid=11",              # ALC245 layouts in AppleALC: 11, 12, 13
    "-vi2c-force-polling",   # touchpad in polling mode first; GPIO interrupts are tested later
    "revpatch=sbvmm,cpuname",
]


def load_bundle_plist(kext_dir: Path) -> dict:
    with open(kext_dir / "Contents" / "Info.plist", "rb") as f:
        return plistlib.load(f)


def kext_entries(kexts_dir: Path) -> list:
    entries, loaded_ids = [], set()
    for rel, enabled, comment in KEXTS:
        path = kexts_dir / rel
        if not path.is_dir():
            sys.exit(f"missing kext bundle: {path}")
        info = load_bundle_plist(path)
        exe = info.get("CFBundleExecutable")
        if exe and not (path / "Contents" / "MacOS" / exe).is_file():
            sys.exit(f"{rel}: executable {exe} not found")
        if enabled:
            # Every non-Apple library a kext links against must be injected before it.
            for lib in info.get("OSBundleLibraries", {}):
                if lib.startswith("com.apple."):
                    continue
                if lib not in loaded_ids:
                    sys.exit(f"{rel}: depends on {lib}, which is not loaded before it")
            loaded_ids.add(info["CFBundleIdentifier"])
        entries.append({
            "Arch": "x86_64",
            "BundlePath": rel,
            "Comment": comment,
            "Enabled": enabled,
            "ExecutablePath": f"Contents/MacOS/{exe}" if exe else "",
            "MaxKernel": "",
            "MinKernel": "",
            "PlistPath": "Contents/Info.plist",
        })
    return entries


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sample")
    ap.add_argument("efi_dir")
    ap.add_argument("--smbios")
    ap.add_argument("--stage", choices=["installer", "installed"], default="installer")
    a = ap.parse_args()

    oc = Path(a.efi_dir) / "OC"
    with open(a.sample, "rb") as f:
        c = plistlib.load(f)
    for k in [k for k in c if k.startswith("#")]:
        del c[k]

    # ACPI: only our SSDTs, no renames or patches.
    c["ACPI"]["Add"] = [
        {"Comment": p.stem, "Enabled": True, "Path": p.name}
        for p in sorted((oc / "ACPI").glob("*.aml"))
    ]
    c["ACPI"]["Delete"] = []
    c["ACPI"]["Patch"] = []

    # Booter: values for Intel 400-series and later firmware (Dortania; OpCore-Simplify rules for
    # Raptor Lake laptops).
    b = c["Booter"]
    b["MmioWhitelist"] = []
    b["Patch"] = []
    b["Quirks"].update({
        "AvoidRuntimeDefrag": True,
        "DevirtualiseMmio": True,
        "EnableSafeModeSlide": True,
        "EnableWriteUnprotector": False,
        "FixupAppleEfiImages": True,
        "ProtectUefiServices": True,
        "ProvideCustomSlide": True,
        "RebuildAppleMemoryMap": True,
        # The RTX 3050 has an 8 GB BAR (Resizable BAR on). 0 keeps the firmware screen alive in the
        # installer; the NVIDIA driver stage switches this to -1 (nullmoth README).
        "ResizeAppleGpuBars": 0 if a.stage == "installer" else -1,
        "SetupVirtualMap": True,
        "SyncRuntimePermissions": True,
    })

    c["DeviceProperties"]["Add"] = {}
    c["DeviceProperties"]["Delete"] = {}

    # Kernel
    k = c["Kernel"]
    k["Add"] = kext_entries(oc / "Kexts")
    # No IONDRVSupport exclude, in either stage. nullmoth blocks it on desktops so the firmware
    # framebuffer does not take NVRMFB's display index, but here the panel is on the Intel iGPU and
    # macOS has no driver for it: the firmware framebuffer is the only thing that shows the panel,
    # and excluding it leaves the built-in screen dark (nullmoth-setup.sh turns it off on such laptops).
    k["Block"] = []
    k["Force"] = []
    k["Patch"] = []
    # macOS has no Raptor Lake CPUID; report Comet Lake (family 6 model 0xA5) as Dortania and
    # OpCore-Simplify do for Alder/Raptor Lake.
    k["Emulate"]["Cpuid1Data"] = bytes.fromhex("55060A00" + "00" * 12)
    k["Emulate"]["Cpuid1Mask"] = bytes.fromhex("FFFFFFFF" + "00" * 12)
    k["Emulate"]["DummyPowerManagement"] = False
    k["Quirks"].update({
        "AppleCpuPmCfgLock": False,
        "AppleXcpmCfgLock": True,        # MSR 0xE2 bit 15 is set and the BIOS has no option for it
        "CustomSMBIOSGuid": True,        # with UpdateSMBIOSMode Custom: Windows keeps the Acer SMBIOS
        "DisableIoMapper": True,         # VT-d stays on for Windows and Linux
        "PanicNoKextDump": True,
        "PowerTimeoutKernelPanic": True,
        "ProvideCurrentCpuInfo": True,   # hybrid P/E-core topology and TSC frequency
        "XhciPortLimit": False,          # every connectable PCH port is at address 15 or lower (ACPI _UPC)
    })

    # Misc
    m = c["Misc"]
    m["BlessOverride"] = []
    m["Entries"] = []
    m["Boot"].update({"PickerMode": "Builtin", "HideAuxiliary": False, "ShowPicker": True,
                      "Timeout": 5, "PollAppleHotKeys": True})
    # Debug: AppleDebug/ApplePanic plus file logging (Target 67) while validating; the DEBUG build of
    # OpenCore is used for the same reason.
    m["Debug"].update({"AppleDebug": True, "ApplePanic": True, "DisableWatchDog": True, "Target": 67})
    m["Security"].update({
        "AllowSetDefault": True,
        "BlacklistAppleUpdate": True,
        "ExposeSensitiveData": 6,
        "ScanPolicy": 0,                 # show every bootable volume (Windows, Linux, recovery)
        "SecureBootModel": "Disabled",   # third-party kexts in /Library/Extensions (nullmoth)
        "Vault": "Optional",
    })
    m["Tools"] = [{
        "Arguments": "", "Auxiliary": True, "Comment": "UEFI shell for debugging",
        "Enabled": True, "Flavour": "OpenShell:UEFIShell:Shell", "FullNvramAccess": False,
        "Name": "UEFI Shell", "Path": "OpenShell.efi", "RealPath": False, "TextMode": False,
    }]

    # NVRAM
    n = c["NVRAM"]
    boot = n["Add"][APPLE_BOOT]
    boot.pop("#INFO (prev-lang:kbd)", None)
    boot["boot-args"] = " ".join(BOOT_ARGS)
    # SIP stays on for the installer; the NVIDIA driver stage needs 0x0A43 (nullmoth README).
    boot["csr-active-config"] = bytes.fromhex("00000000" if a.stage == "installer" else "430A0000")
    boot["prev-lang:kbd"] = b"en-US:0"
    n["Add"][APPLE_VENDOR] = {"revcpu": 1, "revcpuname": "Intel Core i5-13420H"}
    n["Delete"][APPLE_BOOT] = sorted(set(n["Delete"][APPLE_BOOT]) | {"boot-args", "csr-active-config", "prev-lang:kbd"})
    n["Delete"][APPLE_VENDOR] = sorted(set(n["Delete"].get(APPLE_VENDOR, [])) | {"revcpu", "revcpuname"})
    n["WriteFlash"] = True

    # PlatformInfo
    p = c["PlatformInfo"]
    g = p["Generic"]
    g.update({"SystemProductName": SMBIOS_MODEL, "SystemSerialNumber": "", "MLB": "",
              "SystemUUID": "", "ROM": b"", "SpoofVendor": True, "ProcessorType": 0})
    if a.smbios:
        with open(a.smbios) as f:
            s = json.load(f)
        for key in ("SystemProductName", "SystemSerialNumber", "MLB", "SystemUUID"):
            g[key] = s[key]
        g["ROM"] = bytes.fromhex(s["ROM"])
    p["Automatic"] = True
    p["UpdateSMBIOSMode"] = "Custom"

    # UEFI
    u = c["UEFI"]
    u["APFS"].update({"MinDate": -1, "MinVersion": -1})
    u["Drivers"] = [
        {"Arguments": "", "Comment": d, "Enabled": True, "HideVerbose": False, "LoadEarly": False,
         "Path": d}
        for d in ("OpenHfsPlus.efi", "OpenRuntime.efi", "ResetNvramEntry.efi")
    ]
    u["Input"]["KeySupport"] = True
    u["Output"].update({"ProvideConsoleGop": True, "Resolution": "Max"})
    u["Quirks"].update({
        "EnableVectorAcceleration": False,
        "IgnoreInvalidFlexRatio": False,
        "ReleaseUsbOwnership": True,
        "RequestBootVarRouting": True,
        "ResizeGpuBars": -1,
    })
    u["ReservedMemory"] = []

    with open(oc / "config.plist", "wb") as f:
        plistlib.dump(c, f, sort_keys=True)


if __name__ == "__main__":
    main()
