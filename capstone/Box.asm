// Box.asm  --  Capstone, K = 15
// While any key is pressed, draw a black box; when released, clear it.
// Box: starts at row 15, 20 rows tall, 16*((15 mod 4)+1) = 64 pixels wide (4 words).
// First word address = SCREEN + 32*15 = 16384 + 480 = 16864.

(LOOP)
    @KBD
    D=M
    @BLACK
    D;JNE           // key pressed -> black
    @color
    M=0             // no key -> white
    @DRAW
    0;JMP
(BLACK)
    @color
    M=-1            // all 16 bits set = black

(DRAW)
    @16864          // top-left word of the box (row 15, column 0)
    D=A
    @addr
    M=D
    @20             // 20 rows
    D=A
    @rows
    M=D

(ROW)
    @color
    D=M
    @addr
    A=M
    M=D             // word 0  (pixels 0-15)
    A=A+1
    M=D             // word 1  (pixels 16-31)
    A=A+1
    M=D             // word 2  (pixels 32-47)
    A=A+1
    M=D             // word 3  (pixels 48-63)

    @32             // move down one screen row (32 words)
    D=A
    @addr
    M=D+M

    @rows
    MD=M-1
    @ROW
    D;JGT

    @LOOP
    0;JMP
