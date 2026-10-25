"""PE contract checker for CvGameCoreDLL.dll.

Reads machine type, linker version, export names and import names from a PE file
and compares them against golden files. Exit code 0 on match, 1 on mismatch.

  python pe_check.py --dll <path> --golden-dir <dir>            compare
  python pe_check.py --dll <path> --golden-dir <dir> --write    write golden files
"""

import argparse
import struct
import sys
from pathlib import Path

IMAGE_FILE_MACHINE_I386 = 0x14C
PE32_MAGIC = 0x10B
EXPORT_DIR = 0
IMPORT_DIR = 1


class PeError(Exception):
    pass


class Pe:
    def __init__(self, data: bytes):
        self.data = data
        if data[:2] != b"MZ":
            raise PeError("missing MZ signature")
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe:pe + 4] != b"PE\0\0":
            raise PeError("missing PE signature")
        self.machine, nsec, _, _, _, opt_size = struct.unpack_from("<HHIIIH", data, pe + 4)
        self.opt = pe + 24
        if struct.unpack_from("<H", data, self.opt)[0] != PE32_MAGIC:
            raise PeError("not PE32")
        self.linker = (data[self.opt + 2], data[self.opt + 3])
        self.dirs = [struct.unpack_from("<II", data, self.opt + 96 + 8 * i) for i in range(16)]
        sec = self.opt + opt_size
        self.sections = []
        for i in range(nsec):
            vsize, va, rawsize, rawptr = struct.unpack_from("<IIII", data, sec + 40 * i + 8)
            self.sections.append((va, max(vsize, 1), rawptr))

    def offset(self, rva: int) -> int:
        for va, vsize, raw in self.sections:
            if va <= rva < va + vsize:
                return rva - va + raw
        raise PeError(f"RVA 0x{rva:X} not in any section")

    def cstr(self, rva: int) -> str:
        off = self.offset(rva)
        return self.data[off:self.data.index(b"\0", off)].decode("ascii", "replace")

    def exports(self):
        rva, size = self.dirs[EXPORT_DIR]
        if rva == 0:
            return []
        e = self.offset(rva)
        n_names = struct.unpack_from("<I", self.data, e + 24)[0]
        names_off = self.offset(struct.unpack_from("<I", self.data, e + 32)[0])
        return sorted(self.cstr(struct.unpack_from("<I", self.data, names_off + 4 * i)[0])
                      for i in range(n_names))

    def imports(self):
        rva, _ = self.dirs[IMPORT_DIR]
        result = {}
        off = self.offset(rva)
        while True:
            oft, _, _, name_rva, _ = struct.unpack_from("<IIIII", self.data, off)
            if oft == 0 and name_rva == 0:
                break
            dll = self.cstr(name_rva).lower()
            thunk = self.offset(oft)
            funcs = []
            while True:
                val = struct.unpack_from("<I", self.data, thunk)[0]
                if val == 0:
                    break
                if not val & 0x80000000:
                    funcs.append(self.cstr(val + 2))
                thunk += 4
            result[dll] = sorted(funcs)
            off += 20
        return result


def render_imports(imports):
    lines = []
    for dll in sorted(imports):
        lines.append(f"{dll}")
        lines.extend(f"  {fn}" for fn in imports[dll])
    return "\n".join(lines) + "\n"


STRICT_DLLS = ("python24.dll", "boost_python-vc71-mt-1_32.dll")


def strict_view(lines):
    """Keep full function lists only for the Python/Boost ABI; other DLLs reduce to their names."""
    out, keep = [], False
    for line in lines:
        if not line.startswith(" "):
            keep = line in STRICT_DLLS
        if keep or not line.startswith(" "):
            out.append(line)
    return out


def compare(name, actual, expected):
    if actual == expected:
        print(f"PASS {name}: {len(actual)} entries match")
        return True
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    print(f"FAIL {name}: missing {len(missing)}, extra {len(extra)}")
    for line in (missing[:20] + [f"  extra: {x}" for x in extra[:20]]):
        print(f"  {line}")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dll", required=True, type=Path)
    ap.add_argument("--golden-dir", required=True, type=Path)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    pe = Pe(args.dll.read_bytes())
    exports = pe.exports()
    imports = render_imports(pe.imports()).splitlines()
    linker = f"{pe.linker[0]}.{pe.linker[1]}"
    machine_ok = pe.machine == IMAGE_FILE_MACHINE_I386

    gdir = args.golden_dir
    if args.write:
        gdir.mkdir(parents=True, exist_ok=True)
        (gdir / "exports.txt").write_text("\n".join(exports) + "\n", encoding="utf-8")
        (gdir / "imports.txt").write_text("\n".join(imports) + "\n", encoding="utf-8")
        (gdir / "linker.txt").write_text(linker + "\n", encoding="utf-8")
        print(f"WROTE golden: {len(exports)} exports, {len(imports)} import lines, linker {linker}")
        return 0

    ok = machine_ok
    print(("PASS" if machine_ok else "FAIL") + f" machine i386: 0x{pe.machine:04X}")
    print(f"INFO linker {linker} (not a pass/fail criterion; the loader does not check it)")
    golden_exports = (gdir / "exports.txt").read_text(encoding="utf-8").splitlines()
    golden_imports = (gdir / "imports.txt").read_text(encoding="utf-8").splitlines()
    ok &= compare("exports", exports, golden_exports)
    ok &= compare("imports (strict DLLs)", strict_view(imports), strict_view(golden_imports))
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PeError as e:
        print(f"FAIL not a valid PE32 file: {e}")
        sys.exit(1)
