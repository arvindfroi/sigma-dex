@ Small Thumb stubs between Origin's code and nuzlocke.c: places where C cannot see the caller's registers, or where
@ the original call has arguments on the stack that a C wrapper would move.
    .syntax unified
    .thumb
    .text

@ Replaces `bl 0x0205E6F0` (pause map objects, r0 = map object manager) at arm9 0x02050042, in state 0 of the
@ random wild encounter task. There r5 = FieldSystem, r4 = the task's environment.
    .global nz_hook_wild
    .thumb_func
nz_hook_wild:
    push {r0, lr}
    movs r0, r5
    movs r1, r4
    bl nz_on_wild_start
    pop {r0, r1}
    mov lr, r1
    ldr r1, =0x0205E6F1
    bx r1

@ Replaces `bl 0x02051074` at arm9 0x02051278 inside BattleSetup_InitFromFieldSystem (every field battle): r0 setup,
@ r1 FieldSystem, r2 save, r3 location, two more arguments on the stack. We run nz_on_battle_setup(save) first, then
@ jump to the original with every register and the stack exactly as they were.
    .global nz_hook_setup
    .thumb_func
nz_hook_setup:
    push {r0-r3, lr}
    movs r0, r2
    bl nz_on_battle_setup
    pop {r0-r3}
    push {r0}
    ldr r0, [sp, #4]
    mov lr, r0
    ldr r0, =0x02051075
    mov r12, r0
    pop {r0}
    add sp, #4
    bx r12

@ Replaces `ldr r1,=0x114D ; adds r7,r0,#0 ; ldrb r0,[r5,r1]` at overlay 9 0x021EB2A4 (start of the battle Bag's Use
@ handler; the patch puts `adds r7,r0,#0` first, then this call). r4 = the bag's battle arguments (item at +0x18),
@ r5 = the bag's work (category at +0x114D). Allowed: return r0 = category, r1 = 0x114D as the original code had.
@ Refused: print our message with the game's own refusal code at 0x021EB3E6 (Bag stays open, nothing used up).
    .global nz_bag_use
    .thumb_func
nz_bag_use:
    push {lr}
    ldr r1, =0x114D
    ldrb r0, [r5, r1]
    ldrh r1, [r4, #24]
    bl nz_bag_item_check
    cmp r0, #0
    bne 1f
    pop {r0}
    mov lr, r0
    ldr r1, =0x114D
    ldrb r0, [r5, r1]
    bx lr
1:  movs r1, r0
    pop {r0}
    ldr r0, [r5, #16]
    ldr r2, [r5, #24]
    ldr r3, =0x021EB3E7
    bx r3

@ Replaces `adds r0,r4,#0 ; adds r0,#32 ; ldrb r0,[r0]` at overlay 9 0x021EB3D6 (battle Bag, Use on a Ball, r4 =
@ the bag's battle arguments, r5 = the bag's work). The caller then does `cmp r0,#1` and shows message 0x30 when it
@ is 1. In an area already used we show our message 0x31 the same way.
    .global nz_ball_check
    .thumb_func
nz_ball_check:
    ldr r0, =nz_no_catch
    ldrb r0, [r0]
    cmp r0, #0
    bne 1f
    movs r0, r4
    adds r0, #32
    ldrb r0, [r0]
    bx lr
1:  ldr r0, [r5, #16]
    ldr r2, [r5, #24]
    movs r1, #0x31
    ldr r3, =0x021EB3E7
    bx r3

@ Replaces `bl 0x0208FA38` at arm9 0x0207A8E6 (party screen, may this item be used on this Pokemon: r0 party,
@ r1 item, r2 slot, r3 move slot, heap on the stack). Blocked: return 0 (the game says it has no effect and keeps the
@ item). Otherwise jump to the original with registers and stack unchanged.
    .global nz_hook_party_item
    .thumb_func
nz_hook_party_item:
    push {r0-r3, lr}
    bl nz_party_item_blocked
    cmp r0, #0
    bne 1f
    pop {r0-r3}
    push {r0}
    ldr r0, [sp, #4]
    mov lr, r0
    ldr r0, =0x0208FA39
    mov r12, r0
    pop {r0}
    add sp, #4
    bx r12
1:  pop {r0-r3}
    movs r0, #0
    pop {pc}

@ Replaces `bl 0x020731FC` (returns a file index, no arguments) at overlay 16 0x021F211C, right after the PC box
@ loaded the icon palettes: put our grey palettes in place, then the original call.
    .global nz_hook_pc_palettes
    .thumb_func
nz_hook_pc_palettes:
    push {lr}
    bl nz_load_grey_palettes
    pop {r0}
    mov lr, r0
    ldr r0, =0x020731FD
    bx r0

    .pool
