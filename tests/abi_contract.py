"""ABI contract checker for CvGameCoreDLL.dll (stdlib only, PE32 i386).

Checks the surface the game EXE (Civ4BeyondSword.exe) depends on:

  entry_points  names the EXE resolves with GetProcAddress must be exported (golden: entry_points.txt)
  vtables       exported MSVC vtables and their slot counts                 (golden: vtables.txt)
  python        Cy* class names registered with Boost.Python                 (golden: python_classes.txt)
  crt           every C runtime / Python / Boost DLL the DLL imports must also be imported by the EXE
                (only when --exe is given; no golden)

  python abi_contract.py --dll <dll> --exe <exe> --golden-dir <dir>            compare
  python abi_contract.py --dll <dll> --exe <exe> --golden-dir <dir> --write    write vtables/python goldens

Exit code 0 on pass, 1 on any failure. Goldens are regenerated only deliberately (--write).
"""

import argparse
import re
import struct
import sys
from pathlib import Path

from pe_check import Pe, PeError

IMAGE_SCN_CNT_CODE = 0x20
EXPORT_DIR = 0
CRT_PREFIXES = ("msvcr", "msvcp", "python", "boost_python")
PY_CLASS_RE = re.compile(rb"Cy[A-Z][A-Za-z]{2,}\x00")


def code_ranges(data):
    """Return (image_base, [(start_rva, end_rva), ...]) for code sections."""
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    nsec, = struct.unpack_from("<H", data, pe_off + 6)
    opt_size, = struct.unpack_from("<H", data, pe_off + 20)
    opt = pe_off + 24
    image_base, = struct.unpack_from("<I", data, opt + 28)
    sec = opt + opt_size
    ranges = []
    for i in range(nsec):
        vsize, va = struct.unpack_from("<II", data, sec + 40 * i + 8)
        chars, = struct.unpack_from("<I", data, sec + 40 * i + 36)
        if chars & IMAGE_SCN_CNT_CODE:
            ranges.append((va, va + vsize))
    return image_base, ranges


def export_rvas(pe):
    """Map exported name -> RVA using the export directory tables."""
    rva, _ = pe.dirs[EXPORT_DIR]
    if rva == 0:
        return {}
    e = pe.offset(rva)
    n_names = struct.unpack_from("<I", pe.data, e + 24)[0]
    funcs = pe.offset(struct.unpack_from("<I", pe.data, e + 28)[0])
    names = pe.offset(struct.unpack_from("<I", pe.data, e + 32)[0])
    ords = pe.offset(struct.unpack_from("<I", pe.data, e + 36)[0])
    result = {}
    for i in range(n_names):
        name = pe.cstr(struct.unpack_from("<I", pe.data, names + 4 * i)[0])
        ordinal = struct.unpack_from("<H", pe.data, ords + 2 * i)[0]
        result[name] = struct.unpack_from("<I", pe.data, funcs + 4 * ordinal)[0]
    return result


def vtable_slot_rvas(pe, data, rva):
    """RVAs of vtable entries: pointers into code sections, stop at the first that is not."""
    image_base, ranges = code_ranges(data)
    targets = []
    off = pe.offset(rva)
    while off + 4 * (len(targets) + 1) <= len(data):
        target = struct.unpack_from("<I", data, off + 4 * len(targets))[0] - image_base
        if not any(lo <= target < hi for lo, hi in ranges):
            break
        targets.append(target)
    return targets


def vtable_lines(pe, data):
    """One line per exported vtable: its slots, each named by export or <local> if unexported."""
    rvas = export_rvas(pe)
    symbol_at = {}
    for name, rva in rvas.items():
        symbol_at.setdefault(rva, name)
    lines = []
    for name in sorted(rvas):
        if name.startswith("??_7"):
            slots = vtable_slot_rvas(pe, data, rvas[name])
            lines.append(f"{name} {len(slots)} " + " ".join(symbol_at.get(t, "<local>") for t in slots))
    return lines


def python_class_lines(data):
    names = sorted({m.group(0)[:-1].decode("ascii") for m in PY_CLASS_RE.finditer(data)})
    return names


def compare(name, actual, golden_path):
    expected = golden_path.read_text(encoding="utf-8").splitlines()
    if actual == expected:
        print(f"PASS {name}: {len(actual)} entries match")
        return True
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    print(f"FAIL {name}: missing {len(missing)}, extra {len(extra)}")
    for line in missing[:20]:
        print(f"  missing: {line}")
    for line in extra[:20]:
        print(f"  extra: {line}")
    return False


def check_entry_points(pe, golden_dir, exe_data=None):
    exported = set(export_rvas(pe))
    required = (golden_dir / "entry_points.txt").read_text(encoding="utf-8").split()
    missing = [n for n in required if n not in exported]
    if missing:
        print(f"FAIL entry_points: EXE resolves but DLL does not export {missing}")
        return False
    if exe_data is not None:
        unreferenced = [n for n in required if n.encode("ascii") not in exe_data]
        if unreferenced:
            print(f"FAIL entry_points: names absent from the EXE image {unreferenced}")
            return False
    print(f"PASS entry_points: {len(required)} EXE-resolved names exported")
    return True


def check_crt(dll_pe, exe_pe):
    exe_dlls = set(exe_pe.imports())
    dll_dlls = set(dll_pe.imports())
    runtime = {d for d in dll_dlls if d.startswith(CRT_PREFIXES)}
    missing = sorted(runtime - exe_dlls)
    if missing:
        print(f"FAIL crt: DLL imports runtime {missing} that the EXE does not; allocator/CRT mismatch")
        return False
    print(f"PASS crt: DLL runtime imports {sorted(runtime)} are shared with the EXE")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dll", required=True, type=Path)
    ap.add_argument("--exe", type=Path)
    ap.add_argument("--golden-dir", required=True, type=Path)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    data = args.dll.read_bytes()
    pe = Pe(data)
    gdir = args.golden_dir
    vtables = vtable_lines(pe, data)
    pyclasses = python_class_lines(data)

    if args.write:
        gdir.mkdir(parents=True, exist_ok=True)
        (gdir / "vtables.txt").write_text("\n".join(vtables) + "\n", encoding="utf-8")
        (gdir / "python_classes.txt").write_text("\n".join(pyclasses) + "\n", encoding="utf-8")
        print(f"WROTE goldens: {len(vtables)} vtables, {len(pyclasses)} python classes")
        return 0

    exe_data = args.exe.read_bytes() if args.exe else None
    ok = check_entry_points(pe, gdir, exe_data)
    ok &= compare("vtables", vtables, gdir / "vtables.txt")
    ok &= compare("python", pyclasses, gdir / "python_classes.txt")
    if args.exe:
        ok &= check_crt(pe, Pe(args.exe.read_bytes()))
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PeError as e:
        print(f"FAIL not a valid PE32 file: {e}")
        sys.exit(1)
