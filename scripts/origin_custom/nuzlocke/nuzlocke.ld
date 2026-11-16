/* Our resident code: main RAM [0x023D2000, 0x023D4000), right below the advanced trainer AI's region.
   The build lowers the main arena end from 0x023D4000 to 0x023D2000 to give it up. */
MEMORY { nz (rwx) : ORIGIN = 0x023D2000, LENGTH = 0x2000 }
SECTIONS
{
    .text : { *(.text*) *(.rodata*) } > nz
    .data : { *(.data*) } > nz
    .bss : { *(.bss*) *(COMMON) } > nz
    /DISCARD/ : { *(.ARM.exidx*) *(.ARM.attributes) *(.comment) }
}
