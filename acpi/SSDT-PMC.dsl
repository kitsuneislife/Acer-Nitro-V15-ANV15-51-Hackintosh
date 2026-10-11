/*
 * PMC (power management controller) memory region for macOS on the Acer Nitro V 15 ANV15-51.
 *
 * Intel 300-series and later PCHs need this region reserved for native NVRAM to work.
 * The PWRM base on this platform is the standard 0xFE000000.
 *
 * Based on SSDT-PMC.dsl from acidanthera/OpenCorePkg (BSD-3-Clause), with the path moved to PC00.
 */
DefinitionBlock ("", "SSDT", 2, "ANV15", "PMCR", 0x00001000)
{
    External (_SB_.PC00.LPCB, DeviceObj)

    Scope (\_SB.PC00.LPCB)
    {
        Device (PMCR)
        {
            Name (_HID, EisaId ("APP9876"))  // _HID: Hardware ID
            Method (_STA, 0, NotSerialized)  // _STA: Status
            {
                If (_OSI ("Darwin"))
                {
                    Return (0x0B)
                }
                Else
                {
                    Return (Zero)
                }
            }

            Name (_CRS, ResourceTemplate ()  // _CRS: Current Resource Settings
            {
                Memory32Fixed (ReadWrite,
                    0xFE000000,         // Address Base
                    0x00010000,         // Address Length
                    )
            })
        }
    }
}
