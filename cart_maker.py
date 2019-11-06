###############################################################################
#                                                                             #
#   cart_maker.py                                                             #
#                                                                             #
#   Creates an Atari 2600 cartridge binary file "from scratch" (that is,      #
#   without any sort of assembler/editor). The 6502 program instructions      #
#   are all hardcoded here, using raw opcode hex values. Branches and jumps   #
#   are calcuated without the aid of labels.                                  #
#                                                                             #
#   A fun exercise in old-school machine language! Inspired by Ben Eater's    #
#   6502 video: https://www.youtube.com/watch?v=yl8vPW5hydQ                   #
#                                                                             #
###############################################################################


########  Set-up  #############################################################

# Some helper functions to pull out the least and
# most-significant bytes of a 2-byte address
def lsb(word):
    return(word & 0x00FF)

def msb(word):
    return(word >> 8)


# Rom size in bytes (valid values are 2k or 4k)
rom_size = 2 * 1024
pad_byte = 0
file_name = 'rainbows.bin'

# The "reset vector" is the address of where we want code execution to begin.
# We'll make it the first byte of the file, from the point of view of the
# Atari's internal addressing scheme, which "sees" the ROM in several mirrored
# mirrored address ranges. Here, we'll think of the ROM as living in the
# top-most mirrored range (0xF800-0xFFFF for 2k carts and 0xF000-0xFFFF
# for 4k carts)
reset_vector = 0xFFFF - rom_size + 1



###############################################################################
#                                                                             #
#   The actual machine code...                                                #
#                                                                             #
###############################################################################

# Refer to any list of 6502 opcodes, such as
# http://www.6502.org/tutorials/6502opcodes.html
# for all the various hex values we could use here

# We'll define each section of code as a separate bytearray, for flexibility
# and reusability, and to make absolute jump addressing easier to calculate.


# Initialization routine
init_tia = bytearray([
    
    # Set up 6507
    0x78,               # SEI           ; Disable interrupts
    0xD8,               # CLD           ; Disable BCD math mode
    0xA2, 0xFF,         # LDX #$FF
    0x9A,               # TXS           ; Set stack pointer to top of RAM
    0xA9, 0x00,         # LDA #0        ; Set A to zero
    0xE8,               # INX           ; This effectively sets X to zero
    0xA8,               # TAY           ; Zero out Y too
    
    # Clear out TIA registers (this uses A and X, but leaves them at zero)    
    0x95, 0x00,         # STA $00,X     ; Write A's zero to address X
    0xCA,               # DEX           ; Note: Wraps to $FF on first decrement
    0xD0, 0xFB          # BNE -5        ; (to STA $00,X)

    ])



# Vertical blank routine: Signal the television beam to head back up to the
# top and start a new frame. Keep beam off until we're sure we're in the
# visible portion of the screen.
vblank = bytearray([
    
    # Vertical sync
    0xA9, 0x02,         # LDA #2
    0x85, 0x01,         # STA VBLANK    ; Turn on vertical blanking
    0x85, 0x00,         # STA VSYNC     ; Turn on vertical sync
    0x85, 0x02,         # STA WSYNC     ; Three lines of vsync signal
    0x85, 0x02,         # STA WYSNC
    0x85, 0x02,         # STA WSYNC
    0xA9, 0x00,         # LDA #0
    0x85, 0x00,         # STA VSYNC     ; Turn off vertical sync
    
    # Remainder of vertical blanking period (37 lines)
    0xA2, 0x25,         # LDX #37
    
    0x85, 0x02,         # STA WSYNC
    0xCA,               # DEX
    0xD0, 0xFB,         # BNE -5        ; (to STA WSYNC)
    
    0x85, 0x01          # STA VBLANK    ; Turn off vertical blanking
    
    ])


    
# Display the visible area of the frame (192 lines for NTSC,). We change
# the background color every scanline, starting with whatever color is in
# memory location $80 for the top line. Since the least-significant bit is
# ignored for color values, we have to increment it twice to actually get
# a different color.
viz_area = bytearray([
    
    0xA2, 0xC0,         # LDX #192      ; Line count. Use 0xF2 (242) for PAL
    0xA4, 0x80,         # LDY $80       ; Get starting color for this frame
    
    0x84, 0x09,         # STY COLUBK    ; Set the background color
    0xC8,               # INY           ; Increment the color value
    0xC8,               # INY           ; ...twice
    0x85, 0x02,         # STA WSYNC     ; Wait for scanline to end
    0xCA,               # DEX           ; Decrement the line count
    0xD0, 0xF7          # BNE -9        ; (to STY COLUBK)
    
    ])



# Calculate the address of the entry point of main loop, which is five
# bytes into the vblank code chunk (at the first STA VSYNC). We'll use
# this address for the JMP at the end of the following code chunk...
looptop = 0xFFFF - rom_size + len(init_tia) + 5


# Overscan routine: Turn beam off for the final scanlines, ensuring that
# we've covered the bottom area of the screen and beyond. Then jump back
# up to start the next frame. This portion is also a good point to do any
# needed frame-to-frame updates. Here, we'll just change the value held in
# the memory address used to keep track of the starting color for each
# frame, giving us the famous "Atari Rainbow Waterfall" effect.
overscan = bytearray([
    
    # Blank area at bottom of frame (30 total scanlines)
    0xA9, 0x02,         # LDA #2
    0x85, 0x01,         # STA VBLANK
    0xA2, 0x1C,         # LDX #28       ; Waste time for 28 scanlines
    
    0x85, 0x02,         # STA WSYNC
    0xCA,               # DEX
    0xD0, 0xFB,         # BNE -5        ; (to STA WSYNC)
    
    # During the last scanline, adjust starting color
    0xA5, 0x80,         # LDA $80
    0x38,               # SEC           ; Always set the carry flag before SBC!
    0xE9, 0x04,         # SBC #2        ; Change this value to adjust "speed"
    0x85, 0x02,         # STA WSYNC     ; Finish 29th line
    0x85, 0x80,         # STA $80
    0xA9, 0x02,         # LDA #2        ; In prep for the VSYNC at top of loop
    0x85, 0x02,         # STA WSYNC     ; Wait for 30th line to finish
    
    0x4C, lsb(looptop), # JMP to start of main loop. (Note that the 6502 family
          msb(looptop)  # uses "little-endian" addressing, with the lsb first.)

    ])



###############################################################################
#                                                                             #
#   ROM binary build                                                          #
#                                                                             #
###############################################################################

# Just stitch the code chunks together...
rom = init_tia + vblank + viz_area + overscan
code_length = len(rom)

# Fill out the unused portions of the rom
num_pad_bytes = rom_size - code_length
rom = rom + bytearray([pad_byte] * num_pad_bytes)

# Poke the reset vector into the 4th-highest and 3rd-highest bytes, where the
# 6502 microprocessor family is designed to look for it on start-up
rom[rom_size - 5] = lsb(reset_vector)
rom[rom_size - 3] = msb(reset_vector)

# Output the binary
with open(file_name, 'wb') as out_file:
    out_file.write(rom)

# Status report
print()
print('File "' + file_name + '" complete')
print(str(code_length) + ' bytes of program code')
print(str(len(rom)) + ' total bytes on cartridge')
print('Reset vector: ' + f"0x{reset_vector:X}")
print()


