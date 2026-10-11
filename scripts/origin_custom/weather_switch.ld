SECTIONS {
  .handler 0x02238dd8 : { *(.text.handler) }
  .add     0x02238e4c : { *(.text.add) }
}
