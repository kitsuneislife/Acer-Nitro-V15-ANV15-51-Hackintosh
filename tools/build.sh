#!/usr/bin/env bash
# Build the OpenCore EFI folder for the Acer Nitro V 15 ANV15-51 from pinned upstream releases.
#
#   tools/build.sh [--release] [--stage installer|installed] [--smbios FILE]
#
# Output: build/EFI (BOOT/BOOTx64.efi + OC/). The DEBUG build of OpenCore is the default while the
# EFI is validated; --release switches to RELEASE. --smbios fills the serial numbers from a private
# JSON file (never commit it). Downloads are cached in $EFI_CACHE (default: .cache/).
#
# Needs: curl, unzip, sha256sum, iasl (acpica), python3.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="${EFI_CACHE:-$REPO/.cache}"
OUT="$REPO/build"
FLAVOR=DEBUG
STAGE=installer
SMBIOS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --release) FLAVOR=RELEASE ;;
    --stage) STAGE="$2"; shift ;;
    --smbios) SMBIOS=(--smbios "$(realpath "$2")"); shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

for tool in curl unzip sha256sum iasl python3; do
  command -v "$tool" >/dev/null || { echo "missing tool: $tool" >&2; exit 1; }
done

mkdir -p "$CACHE"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# 1. Fetch and verify every pinned release.
while IFS=$'\t' read -r name url sum; do
  [[ -z "$name" || "$name" == \#* ]] && continue
  if [[ ! -f "$CACHE/$name" ]]; then
    echo "fetch $name"
    curl -fsSL -o "$CACHE/$name.partial" "$url"
    mv "$CACHE/$name.partial" "$CACHE/$name"
  fi
  echo "$sum  $CACHE/$name" | sha256sum -c --quiet - || { echo "checksum mismatch: $name" >&2; exit 1; }
  mkdir -p "$WORK/${name%.zip}"
  unzip -q "$CACHE/$name" -d "$WORK/${name%.zip}"
  rm -rf "$WORK/${name%.zip}/__MACOSX"
done < "$REPO/tools/sources.tsv"

OCZ="$WORK/OpenCore-1.0.8-$FLAVOR"
OCR="$WORK/OpenCore-1.0.8-RELEASE"   # Sample.plist and the Linux ocvalidate ship in both flavours

# 2. OpenCore skeleton: only the drivers and tools the config uses.
rm -rf "$OUT"
mkdir -p "$OUT/EFI/BOOT" "$OUT/EFI/OC"/{ACPI,Drivers,Kexts,Tools,Resources}
cp "$OCZ/X64/EFI/BOOT/BOOTx64.efi" "$OUT/EFI/BOOT/"
cp "$OCZ/X64/EFI/OC/OpenCore.efi" "$OUT/EFI/OC/"
for d in OpenHfsPlus OpenRuntime ResetNvramEntry; do
  cp "$OCZ/X64/EFI/OC/Drivers/$d.efi" "$OUT/EFI/OC/Drivers/"
done
cp "$OCZ/X64/EFI/OC/Tools/OpenShell.efi" "$OUT/EFI/OC/Tools/"

# 3. ACPI: compile our SSDTs (warnings about the legacy Processor() keyword are expected).
for dsl in "$REPO"/acpi/*.dsl; do
  base="$(basename "${dsl%.dsl}")"
  iasl -vs -p "$OUT/EFI/OC/ACPI/$base" "$dsl" >"$WORK/iasl-$base.log" 2>&1 \
    || { cat "$WORK/iasl-$base.log" >&2; exit 1; }
  grep -q ' 0 Errors' "$WORK/iasl-$base.log" || { cat "$WORK/iasl-$base.log" >&2; exit 1; }
done

# 4. Kexts.
K="$OUT/EFI/OC/Kexts"
cp -R "$WORK/Lilu-1.7.2-RELEASE/Lilu.kext" "$K/"
for x in VirtualSMC SMCProcessor SMCBatteryManager; do
  cp -R "$WORK/VirtualSMC-1.3.8-RELEASE/Kexts/$x.kext" "$K/"
done
cp -R "$WORK/AppleALC-1.9.8-RELEASE/AppleALC.kext" "$K/"
cp -R "$WORK/RestrictEvents-1.1.6-RELEASE/RestrictEvents.kext" "$K/"
cp -R "$WORK/NVMeFix-1.1.3-RELEASE/NVMeFix.kext" "$K/"
cp -R "$WORK/BrightnessKeys-1.0.3-RELEASE/BrightnessKeys.kext" "$K/"
cp -R "$WORK/ECEnabler-1.0.6-RELEASE/ECEnabler.kext" "$K/"
cp -R "$WORK/CpuTopologyRebuild-2.0.2-RELEASE/CpuTopologyRebuild.kext" "$K/"
cp -R "$WORK/VoodooPS2Controller-2.3.7-RELEASE/VoodooPS2Controller.kext" "$K/"
cp -R "$WORK/VoodooI2C-2.9.1-RELEASE/VoodooI2C.kext" "$K/"
cp -R "$WORK/VoodooI2C-2.9.1-RELEASE/VoodooI2CHID.kext" "$K/"
cp -R "$WORK/RealtekRTL8111-V3.0.0/RealtekRTL8111-V3.0.0/Release/RealtekRTL8111.kext" "$K/"
for x in SimpleMtkBtFw SimpleMtkBtPatcher; do
  cp -R "$WORK/SimpleMtkBtFw-1.0.0-RELEASE/SimpleMtkBtFw-1.0.0-RELEASE/$x.kext" "$K/"
done

# VoodooI2C 2.9.1 does not match the Alder/Raptor Lake PCH I2C controller (8086:51E8).
# Add it to the Lake controller personality, as Alder Lake laptop EFIs do.
python3 - "$K/VoodooI2C.kext/Contents/Info.plist" <<'EOF'
import plistlib, sys
path = sys.argv[1]
with open(path, "rb") as f:
    p = plistlib.load(f)
pers = p["IOKitPersonalities"]["VoodooI2CPCILakeController"]
ids = pers["IOPCIMatch"].split()
if "0x51e88086&0xFFFCFFFF" not in ids:
    pers["IOPCIMatch"] = " ".join(["0x51e88086&0xFFFCFFFF"] + ids)
with open(path, "wb") as f:
    plistlib.dump(p, f)
EOF

# 5. config.plist.
python3 "$REPO/tools/make_config.py" "$OCR/Docs/Sample.plist" "$OUT/EFI" --stage "$STAGE" "${SMBIOS[@]}"

# 6. Validate.
OCV="$OCR/Utilities/ocvalidate/ocvalidate.linux"
chmod +x "$OCV"
"$OCV" "$OUT/EFI/OC/config.plist"

echo "built $OUT/EFI ($FLAVOR, stage $STAGE)"
