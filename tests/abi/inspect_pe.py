"""Dev-only inspection of Civ4 PE binaries (requires the pixi 'dev' environment: pefile, capstone).

  pixi run --environment dev python tests/abi/inspect_pe.py --file <exe-or-dll>
  pixi run --environment dev python tests/abi/inspect_pe.py --file <dll> --disasm "?DLLPublishToPython@@YAXXZ"
"""

import argparse
import sys
from pathlib import Path

import capstone
import pefile

IMAGE_SCN_CNT_CODE = 0x20


def code_ranges(pe):
    base = pe.OPTIONAL_HEADER.ImageBase
    out = []
    for s in pe.sections:
        if s.Characteristics & IMAGE_SCN_CNT_CODE:
            out.append((s.VirtualAddress, s.VirtualAddress + s.Misc_VirtualSize))
    return base, out


def vtable_slots(pe, rva):
    """Count entries of an MSVC vtable: pointers into code sections, stop at the first that is not."""
    base, ranges = code_ranges(pe)
    slots = 0
    while True:
        value = pe.get_dword_at_rva(rva + 4 * slots)
        if value is None:
            break
        target = value - base
        if not any(lo <= target < hi for lo, hi in ranges):
            break
        slots += 1
    return slots


def dump(path):
    pe = pefile.PE(str(path))
    print(f"FILE {path.name}")
    print(f"  machine 0x{pe.FILE_HEADER.Machine:04X}  subsystem {pe.OPTIONAL_HEADER.Subsystem}  "
          f"linker {pe.OPTIONAL_HEADER.MajorLinkerVersion}.{pe.OPTIONAL_HEADER.MinorLinkerVersion}  "
          f"imagebase 0x{pe.OPTIONAL_HEADER.ImageBase:08X}")
    print("  sections: " + ", ".join(s.Name.rstrip(b"\0").decode() for s in pe.sections))

    print("  imports:")
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        names = [imp.name.decode() if imp.name else f"ord{imp.ordinal}" for imp in entry.imports]
        print(f"    {entry.dll.decode()} ({len(names)})")
        for n in names:
            print(f"      {n}")

    exports = []
    if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        exports = [s.name.decode() for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name]
    print(f"  exports: {len(exports)}")

    print("  exported vtables (slot count):")
    for sym in pe.DIRECTORY_ENTRY_EXPORT.symbols if hasattr(pe, "DIRECTORY_ENTRY_EXPORT") else []:
        if sym.name and sym.name.startswith(b"??_7"):
            print(f"    {sym.name.decode()} = {vtable_slots(pe, sym.address)}")
    return pe


def disasm(pe, symbol):
    for sym in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if sym.name == symbol.encode():
            base = pe.OPTIONAL_HEADER.ImageBase
            code = pe.get_memory_mapped_image()[sym.address:sym.address + 64]
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
            print(f"disasm {symbol} at 0x{base + sym.address:08X}")
            for ins in md.disasm(code, base + sym.address):
                print(f"  0x{ins.address:08X}  {ins.mnemonic} {ins.op_str}")
                if ins.mnemonic == "ret":
                    break
            return
    print(f"symbol not exported: {symbol}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, type=Path, action="append")
    ap.add_argument("--disasm", help="exported symbol to disassemble (first 64 bytes)")
    args = ap.parse_args()
    for f in args.file:
        pe = dump(f)
        if args.disasm:
            disasm(pe, args.disasm)
    return 0


if __name__ == "__main__":
    sys.exit(main())
