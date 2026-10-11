/*
 * Fake EC device and USB power properties for macOS on the Acer Nitro V 15 ANV15-51.
 *
 * The real embedded controller is \_SB.PC00.LPCB.EC0 (PNP0C09). On a laptop it must stay enabled
 * (battery, fans, hotkeys), so unlike the desktop sample this does not disable EC0. It only adds a
 * Darwin-only device named EC, which AppleBusPowerController expects, and USBX with the USB power
 * limits macOS uses for charging.
 *
 * Based on SSDT-EC-USBX.dsl from acidanthera/OpenCorePkg (BSD-3-Clause) and the Dortania laptop variant.
 */
DefinitionBlock ("", "SSDT", 2, "ANV15", "SsdtEC", 0x00001000)
{
    External (_SB_.PC00.LPCB, DeviceObj)

    Scope (\_SB.PC00.LPCB)
    {
        Device (EC)
        {
            Name (_HID, "ACID0001")  // _HID: Hardware ID
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
    }

    Scope (\_SB)
    {
        Device (USBX)
        {
            Name (_ADR, Zero)  // _ADR: Address
            Method (_DSM, 4, NotSerialized)  // _DSM: Device-Specific Method
            {
                If ((Arg2 == Zero))
                {
                    Return (Buffer (One)
                    {
                         0x03
                    })
                }

                Return (Package (0x08)
                {
                    "kUSBSleepPowerSupply",
                    0x13EC,
                    "kUSBSleepPortCurrentLimit",
                    0x0834,
                    "kUSBWakePowerSupply",
                    0x13EC,
                    "kUSBWakePortCurrentLimit",
                    0x0834
                })
            }

            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0F)
                }
                Else
                {
                    Return (Zero)
                }
            }
        }
    }
}
