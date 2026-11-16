@ Small Thumb stubs between Origin's code and nuzlocke.c (the places where C cannot see the caller's registers).
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

@ Replaces `adds r0,r4,#0 ; adds r0,#32 ; ldrb r0,[r0]` at overlay 9 0x021EB3D6 (battle Bag, Use on a Ball,
@ r4 = the bag's battle arguments, r5 = the bag's work). The caller then does `cmp r0,#1` and shows message 0x30
@ when it is 1. In an area already used we show our own message 0x31 the same way (the game's code from
@ 0x021EB3E6 prints it, keeps the Ball and returns to the Bag).
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

    .pool
