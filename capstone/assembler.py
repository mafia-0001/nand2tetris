#!/usr/bin/env python3
"""Hack assembler (Nand to Tetris, project 6).

Usage:  python assembler.py Prog.asm        ->  writes Prog.hack

Extra feature (K = 15, K mod 3 = 0):
    Save all labels and variables with their addresses in symbols.txt.
"""
import re
import sys

# ---------------------------------------------------------------- tables
COMP = {
    "0": "0101010", "1": "0111111", "-1": "0111010",
    "D": "0001100", "A": "0110000", "!D": "0001101", "!A": "0110001",
    "-D": "0001111", "-A": "0110011", "D+1": "0011111", "A+1": "0110111",
    "D-1": "0001110", "A-1": "0110010", "D+A": "0000010", "D-A": "0010011",
    "A-D": "0000111", "D&A": "0000000", "D|A": "0010101",
    "M": "1110000", "!M": "1110001", "-M": "1110011", "M+1": "1110111",
    "M-1": "1110010", "D+M": "1000010", "D-M": "1010011", "M-D": "1000111",
    "D&M": "1000000", "D|M": "1010101",
}
DEST = {
    "": "000", "M": "001", "D": "010", "MD": "011",
    "A": "100", "AM": "101", "AD": "110", "AMD": "111",
}
JUMP = {
    "": "000", "JGT": "001", "JEQ": "010", "JGE": "011",
    "JLT": "100", "JNE": "101", "JLE": "110", "JMP": "111",
}
PREDEFINED = {
    "SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
    "SCREEN": 16384, "KBD": 24576,
}
for i in range(16):
    PREDEFINED["R%d" % i] = i

SYMBOL_RE = re.compile(r"^[A-Za-z_.$:][A-Za-z0-9_.$:]*$")


def clean(line):
    """Remove comments and ALL whitespace."""
    return re.sub(r"\s+", "", line.split("//", 1)[0])


def normalise_comp(comp):
    """Allow commutative forms such as A+D, M+D, A|D, M&D."""
    if comp in COMP:
        return comp
    for op in "+&|":
        if op in comp:
            parts = comp.split(op)
            if len(parts) == 2:
                swapped = parts[1] + op + parts[0]
                if swapped in COMP:
                    return swapped
    return comp


def dest_bits(dest):
    """Return the 3 dest bits, or None if invalid.
    Any order of the letters A, M, D is accepted (e.g. MD and DM), each
    letter at most once -- Pong.asm uses 'DM'."""
    if len(set(dest)) != len(dest) or any(c not in "AMD" for c in dest):
        return None
    return ("1" if "A" in dest else "0") + \
           ("1" if "D" in dest else "0") + \
           ("1" if "M" in dest else "0")


def assemble(lines):
    """Return (list_of_16bit_strings, symbol_table, errors)."""
    errors = []
    symbols = dict(PREDEFINED)

    # ---------------- first reading: strip + record labels --------------
    program = []            # (line_number, text)
    rom_address = 0
    for number, raw in enumerate(lines, start=1):
        text = clean(raw)
        if not text:
            continue
        if text.startswith("("):
            if not text.endswith(")") or not SYMBOL_RE.match(text[1:-1]):
                errors.append("Line %d: invalid label '%s'" % (number, text))
                continue
            label = text[1:-1]
            if label in symbols:
                errors.append("Line %d: label '%s' is already defined"
                              % (number, label))
                continue
            symbols[label] = rom_address
            continue
        program.append((number, text))
        rom_address += 1

    # ---------------- second reading: translate to 16 bits -------------
    next_variable = 16
    output = []
    for number, text in program:
        if text.startswith("@"):                       # A-instruction
            value = text[1:]
            if value == "":
                errors.append("Line %d: invalid instruction '@' "
                              "(missing address or symbol)" % number)
                continue
            if value.isdigit():
                n = int(value)
                if n > 32767:
                    errors.append("Line %d: address %d is too large "
                                  "(maximum is 32767)" % (number, n))
                    continue
            elif SYMBOL_RE.match(value):
                if value not in symbols:
                    symbols[value] = next_variable
                    next_variable += 1
                n = symbols[value]
            else:
                errors.append("Line %d: invalid instruction '%s' "
                              "(bad symbol name)" % (number, text))
                continue
            output.append(format(n, "016b"))
        else:                                           # C-instruction
            dest, jump = "", ""
            body = text
            if "=" in body:
                dest, body = body.split("=", 1)
            if ";" in body:
                body, jump = body.split(";", 1)
            comp = normalise_comp(body)
            problem = None
            if body == "":
                problem = "invalid instruction '%s' (missing computation)" % text
            elif dest_bits(dest) is None:
                problem = "invalid destination '%s'" % dest
            elif comp not in COMP:
                problem = "invalid computation '%s'" % body
            elif jump not in JUMP:
                problem = "invalid jump '%s'" % jump
            if problem:
                errors.append("Line %d: %s" % (number, problem))
                continue
            output.append("111" + COMP[comp] + dest_bits(dest) + JUMP[jump])

    # errors from the two readings are reported in line order
    errors.sort(key=lambda m: int(m.split()[1].rstrip(":")))
    return output, symbols, errors


def main():
    if len(sys.argv) != 2:
        print("Usage: python assembler.py Prog.asm")
        return 2
    path = sys.argv[1]
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except OSError as e:
        print("Cannot open '%s': %s" % (path, e.strerror))
        return 2

    output, symbols, errors = assemble(lines)
    if errors:
        for message in errors:
            print(message)
        print("%d error(s) found. No .hack file written." % len(errors))
        return 1

    out_path = path[:-4] + ".hack" if path.endswith(".asm") else path + ".hack"
    with open(out_path, "w") as f:
        f.write("\n".join(output) + "\n")
    print("Wrote %s (%d instructions)" % (out_path, len(output)))

    user_symbols = [
        "%s = %d" % (name, addr)
        for name, addr in symbols.items()
        if name not in PREDEFINED
    ]
    with open("symbols.txt", "w") as f:
        f.write("\n".join(user_symbols) + ("\n" if user_symbols else ""))
    print("Saved %d labels/variables to symbols.txt" % len(user_symbols))
    return 0


if __name__ == "__main__":
    sys.exit(main())
