# Cart Maker

Builds a simple Atari 2600 cartridge binary file "from scratch" using hardcoded Python bytearrays of machine code. Takes care of padding out the binary to the full cartridge size (either 2K or 4K) and sets the reset vector appropriately.

Inspired by Ben Eater's [6502 video](https://www.youtube.com/watch?v=yl8vPW5hydQ), where he flashes an EEPROM using a similar method.

A fun exercise in old-school, bare-metal programming. Opcodes are specified as raw hex values (with careful attention paid to addressing modes). Branches and jumps are calcuated without the aid of labels. Really renews one's appreciation for a good assembler program! :-)

### Example Run

Running the Python script prints out a status report and generates `rainbows.bin`:

![console output](https://github.com/JeffJetton/cart-maker/blob/master/images/console_output.png)

This binary file can be run in any 2600 emulator (or even in a real console if you have something like the [Harmony Cartridge](https://harmony.atariage.com/Site/Harmony.html)). The cartridge produces a version of the famous "Atari rainbow" effect:

![emulator output](https://github.com/JeffJetton/cart-maker/blob/master/images/stella.png)
