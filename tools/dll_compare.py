"""Compare PE DLLs: headers, sections, exports, imports, and raw section bytes.

Usage:
  pixi run -e dev python tools/dll_compare.py REFERENCE.dll OTHER.dll [OTHER2.dll ...]
      [--runs N] [--pointer-deltas]

Every OTHER is compared against REFERENCE. Deltas are OTHER minus REFERENCE.
Byte differences are split into those on base-relocation (HIGHLOW) sites and those elsewhere.
"""
import argparse
import struct
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

HIGHLOW = 3
DIR_NAMES = ["export", "import", "resource", "exception", "security", "basereloc", "debug"]


class Section(NamedTuple):
    name: str
    va: int
    vsize: int
    rawptr: int
    rawsize: int
    chars: int


class Pe:
    def __init__(self, path):
        self.path = Path(path)
        self.d = self.path.read_bytes()
        if self.d[:2] != b"MZ":
            raise ValueError(f"{path}: not a PE file")
        e = struct.unpack_from("<I", self.d, 0x3C)[0]
        if self.d[e:e + 4] != b"PE\0\0":
            raise ValueError(f"{path}: missing PE signature")
        self.size = len(self.d)
        self.timestamp = struct.unpack_from("<I", self.d, e + 8)[0]
        nsec = struct.unpack_from("<H", self.d, e + 6)[0]
        opt_size = struct.unpack_from("<H", self.d, e + 20)[0]
        opt = e + 24
        self.opt = opt
        self.linker = f"{self.d[opt + 2]}.{self.d[opt + 3]}"
        self.image_base = struct.unpack_from("<I", self.d, opt + 28)[0]
        self.size_of_image = struct.unpack_from("<I", self.d, opt + 56)[0]
        self.checksum = struct.unpack_from("<I", self.d, opt + 64)[0]
        self.dll_chars = struct.unpack_from("<H", self.d, opt + 70)[0]
        self.dirs = {}
        for i, name in enumerate(DIR_NAMES):
            self.dirs[name] = struct.unpack_from("<II", self.d, opt + 96 + 8 * i)
        self.sections = []
        first = opt + opt_size
        for i in range(nsec):
            b = first + 40 * i
            name = self.d[b:b + 8].rstrip(b"\0").decode("latin1")
            vsize, va, rawsize, rawptr = struct.unpack_from("<IIII", self.d, b + 8)
            chars = struct.unpack_from("<I", self.d, b + 36)[0]
            self.sections.append(Section(name, va, vsize, rawptr, rawsize, chars))

    def section(self, name):
        return next((s for s in self.sections if s.name == name), None)

    def section_for_rva(self, rva):
        for s in self.sections:
            if s.va <= rva < s.va + max(s.vsize, s.rawsize):
                return s
        return None

    def rva_to_off(self, rva):
        s = self.section_for_rva(rva)
        if s is None:
            raise ValueError(f"{self.path.name}: RVA 0x{rva:X} is outside all sections")
        return rva - s.va + s.rawptr

    def section_bytes(self, s):
        return self.d[s.rawptr:s.rawptr + s.vsize]

    def cstr(self, rva):
        o = self.rva_to_off(rva)
        return self.d[o:self.d.index(b"\0", o)].decode("latin1")

    def reloc_sites(self):
        """RVAs of every 4-byte HIGHLOW fixup in the base relocation table."""
        rva, size = self.dirs["basereloc"]
        sites = set()
        if not rva:
            return sites
        pos = self.rva_to_off(rva)
        end = pos + size
        while pos < end:
            page, block = struct.unpack_from("<II", self.d, pos)
            if block < 8:
                break
            for j in range((block - 8) // 2):
                ent = struct.unpack_from("<H", self.d, pos + 8 + 2 * j)[0]
                if ent >> 12 == HIGHLOW:
                    sites.add(page + (ent & 0xFFF))
            pos += block
        return sites

    def exports(self):
        """Map export name (or '#ordinalN' if unnamed) to (ordinal, function RVA)."""
        rva, _ = self.dirs["export"]
        if not rva:
            return {}
        o = self.rva_to_off(rva)
        (_, _, _, _, _, base, nfunc, nnames,
         funcs_rva, names_rva, ords_rva) = struct.unpack_from("<IIHHIIIIIII", self.d, o)
        fo = self.rva_to_off(funcs_rva)
        no = self.rva_to_off(names_rva)
        oo = self.rva_to_off(ords_rva)
        funcs = [struct.unpack_from("<I", self.d, fo + 4 * i)[0] for i in range(nfunc)]
        named = {}
        for i in range(nnames):
            name = self.cstr(struct.unpack_from("<I", self.d, no + 4 * i)[0])
            idx = struct.unpack_from("<H", self.d, oo + 2 * i)[0]
            named[idx] = name
        out = {}
        for idx in range(nfunc):
            if funcs[idx] == 0:
                continue
            out[named.get(idx, f"#ordinal{base + idx}")] = (base + idx, funcs[idx])
        return out

    def imports(self):
        """Set of (dll, function) pairs. Ordinal-only imports appear as '#ordinalN'."""
        rva, _ = self.dirs["import"]
        out = set()
        if not rva:
            return out
        o = self.rva_to_off(rva)
        while True:
            oft, _, _, name_rva, ft = struct.unpack_from("<IIIII", self.d, o)
            if not (oft or name_rva or ft):
                break
            dll = self.cstr(name_rva).lower()
            lo = self.rva_to_off(oft or ft)
            i = 0
            while True:
                entry = struct.unpack_from("<I", self.d, lo + 4 * i)[0]
                if entry == 0:
                    break
                if entry & 0x80000000:
                    fn = f"#ordinal{entry & 0xFFFF}"
                else:
                    fn = self.cstr(entry + 2)
                out.add((dll, fn))
                i += 1
            o += 20
        return out


def covered(sites):
    out = set()
    for s in sites:
        out.update(range(s, s + 4))
    return out


def run_spans(indices):
    spans = []
    for i in indices:
        if spans and i == spans[-1][1] + 1:
            spans[-1][1] = i
        else:
            spans.append([i, i])
    return spans


def mark(a, b):
    return "same" if a == b else "DIFFERS"


def print_headers(ref, oth):
    print("headers")
    rows = [
        ("file size", ref.size, oth.size),
        ("timestamp (UTC)", datetime.fromtimestamp(ref.timestamp, timezone.utc).isoformat(),
         datetime.fromtimestamp(oth.timestamp, timezone.utc).isoformat()),
        ("linker version", ref.linker, oth.linker),
        ("checksum", f"0x{ref.checksum:08X}", f"0x{oth.checksum:08X}"),
        ("image base", f"0x{ref.image_base:08X}", f"0x{oth.image_base:08X}"),
        ("size of image", f"0x{ref.size_of_image:X}", f"0x{oth.size_of_image:X}"),
        ("DllCharacteristics", f"0x{ref.dll_chars:04X}", f"0x{oth.dll_chars:04X}"),
        ("security dir (file offset, size)", ref.dirs["security"], oth.dirs["security"]),
        ("export dir (rva, size)", ref.dirs["export"], oth.dirs["export"]),
        ("import dir (rva, size)", ref.dirs["import"], oth.dirs["import"]),
        ("basereloc dir (rva, size)", ref.dirs["basereloc"], oth.dirs["basereloc"]),
    ]
    for label, a, b in rows:
        a_s = tuple(f"0x{x:X}" for x in a) if isinstance(a, tuple) else a
        b_s = tuple(f"0x{x:X}" for x in b) if isinstance(b, tuple) else b
        print(f"  {label:34} ref {a_s!s:45} other {b_s!s:45} {mark(a, b)}")


def print_sections(ref, oth):
    print("sections (VirtualSize, VA, RawSize, RawPtr, Characteristics)")
    names = [s.name for s in ref.sections] + [s.name for s in oth.sections if not ref.section(s.name)]
    for name in dict.fromkeys(names):
        a, b = ref.section(name), oth.section(name)
        if a is None or b is None:
            print(f"  {name:8} present only in {'ref' if b is None else 'other'}")
            continue
        fields = ("vsize", "va", "rawsize", "rawptr", "chars")
        same = all(getattr(a, f) == getattr(b, f) for f in fields)
        print(f"  {name:8} ref vsize 0x{a.vsize:06X} va 0x{a.va:06X} rawsize 0x{a.rawsize:06X} rawptr 0x{a.rawptr:06X} chars 0x{a.chars:08X}")
        if not same:
            print(f"  {'':8} other vsize 0x{b.vsize:06X} va 0x{b.va:06X} rawsize 0x{b.rawsize:06X} rawptr 0x{b.rawptr:06X} chars 0x{b.chars:08X}  DIFFERS")


def print_exports(ref, oth):
    re_, oe = ref.exports(), oth.exports()
    common = set(re_) & set(oe)
    only_r = sorted(set(re_) - set(oe))
    only_o = sorted(set(oe) - set(re_))
    ord_mis = [n for n in common if re_[n][0] != oe[n][0]]
    print("exports")
    print(f"  ref {len(re_)}, other {len(oe)}, only in ref {len(only_r)}, only in other {len(only_o)}, ordinal mismatches {len(ord_mis)}")
    for n in only_r[:10]:
        print(f"    only in ref: {n}")
    for n in only_o[:10]:
        print(f"    only in other: {n}")
    deltas = Counter(oe[n][1] - re_[n][1] for n in common)
    differing = len(common) - deltas.get(0, 0)
    print(f"  function RVAs: identical {deltas.get(0, 0)}, differing {differing}")
    for delta, count in deltas.most_common(8):
        if delta:
            print(f"    delta {delta:+d}: {count}")


def print_imports(ref, oth):
    ri, oi = ref.imports(), oth.imports()
    print("imports")
    dlls = sorted({d for d, _ in ri | oi})
    for d in dlls:
        a = sum(1 for x in ri if x[0] == d)
        b = sum(1 for x in oi if x[0] == d)
        print(f"  {d:34} ref {a:4}, other {b:4}")
    only_r = sorted(ri - oi)
    only_o = sorted(oi - ri)
    print(f"  total ref {len(ri)}, other {len(oi)}, identical sets {not only_r and not only_o}")
    for item in only_r[:10]:
        print(f"    only in ref: {item}")
    for item in only_o[:10]:
        print(f"    only in other: {item}")


def pointer_report(ref, oth, rs, os_, diffs, rsites):
    hist = Counter()
    seen = set()
    for i in diffs:
        for start in range(i - 3, i + 1):
            site = rs.va + start
            if start < 0 or site not in rsites or site in seen:
                continue
            seen.add(site)
            a = struct.unpack_from("<I", ref.d, rs.rawptr + start)[0]
            b = struct.unpack_from("<I", oth.d, os_.rawptr + start)[0]
            if a == b:
                continue
            target_ref = a - ref.image_base
            target_oth = b - oth.image_base
            sec = ref.section_for_rva(target_ref)
            label = sec.name if sec else "non-address"
            hist[(label, target_oth - target_ref)] += 1
    print(f"    relocation fields with differing values: {len(seen)} sites examined")
    for (label, delta), count in hist.most_common(10):
        print(f"      target {label:12} delta {delta:+d}: {count}")


def print_bytes(ref, oth, runs, pointer_deltas):
    rsites = ref.reloc_sites()
    osites = oth.reloc_sites()
    rcov = covered(rsites)
    ocov = covered(osites)
    print("section bytes")
    print(f"  relocation sites: ref {len(rsites)}, other {len(osites)}")
    for rs in ref.sections:
        os_ = oth.section(rs.name)
        if os_ is None:
            print(f"  {rs.name:8} missing in other")
            continue
        a = ref.section_bytes(rs)
        b = oth.section_bytes(os_)
        n = min(len(a), len(b))
        diffs = [i for i in range(n) if a[i] != b[i]]
        on_reloc = sum(1 for i in diffs if rs.va + i in rcov or os_.va + i in ocov)
        print(f"  {rs.name:8} compared {n} bytes, differing {len(diffs)}, on reloc sites {on_reloc}, elsewhere {len(diffs) - on_reloc}")
        for start, end in run_spans(diffs)[:runs]:
            print(f"      ref RVA 0x{rs.va + start:08X} length {end - start + 1}")
        if pointer_deltas and diffs:
            pointer_report(ref, oth, rs, os_, diffs, rsites)


def compare(ref, oth, args):
    print(f"== reference {ref.path.name} vs other {oth.path.name}")
    print_headers(ref, oth)
    print_sections(ref, oth)
    print_exports(ref, oth)
    print_imports(ref, oth)
    print_bytes(ref, oth, args.runs, args.pointer_deltas)
    print()


def main(argv=None):
    p = argparse.ArgumentParser(description="Compare PE DLLs against a reference DLL.")
    p.add_argument("reference", help="reference DLL")
    p.add_argument("others", nargs="+", help="DLLs to compare against the reference")
    p.add_argument("--runs", type=int, default=0, help="list the first N differing byte runs per section")
    p.add_argument("--pointer-deltas", action="store_true",
                   help="histogram target section and delta for differing relocation fields")
    args = p.parse_args(argv)
    ref = Pe(args.reference)
    for other in args.others:
        compare(ref, Pe(other), args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
