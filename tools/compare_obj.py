#!/usr/bin/env python3
"""Compare COFF .obj files section by section against a reference build.

Objects are matched by name: "<x>.cpp.obj" in --ours is compared with "<x>.obj" in --ref.
Section raw bytes are compared exactly, and relocations are compared by
(offset, type, target symbol name) so that differences in symbol placement are
distinguished from differences in code.

Example:
    pixi run -e dev python tools/compare_obj.py --ref "C:\\path\\to\\Final Release"
"""

from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OURS = REPO_ROOT / "build" / "final-release-vc7" / "CMakeFiles" / "CVGAMECOREDLL.dir" / "src"
DEFAULT_SECTIONS = ".text,.data,.rdata"
# x86 DIR32 / REL32 relocation sites are 4 bytes wide.
RELOC_SITE_WIDTH = 4


@dataclass
class Section:
    name: str
    key: str  # defining symbol name for COMDAT sections, so order does not matter
    raw: bytes
    relocs: list[tuple[int, int, str]]  # (offset, type, target symbol), sorted


@dataclass
class Coff:
    sections: dict[str, dict[str, Section]] = field(default_factory=dict)


@dataclass
class ObjResult:
    name: str
    issues: list[str] = field(default_factory=list)
    diff_bytes: int = 0
    reloc_site_diff_bytes: int = 0
    other_diff_bytes: int = 0

    @property
    def identical(self) -> bool:
        return not self.issues and self.diff_bytes == 0


def parse_coff(data: bytes) -> Coff:
    _machine, nsec, _ts, symptr, nsym, optsz, _chars = struct.unpack_from("<HHIIIHH", data, 0)
    strtab = symptr + 18 * nsym

    def read_str(off: int) -> str:
        end = data.index(b"\0", off)
        return data[off:end].decode("ascii", "replace")

    # Symbol table index -> name. Aux records get placeholder entries so indices stay valid.
    symbols: list[str] = []
    defined_by_section: dict[int, str] = {}  # 1-based section number -> defining function name
    i = 0
    while i < nsym:
        e = symptr + 18 * i
        if data[e:e + 4] == b"\0\0\0\0":
            name = read_str(strtab + struct.unpack_from("<I", data, e + 4)[0])
        else:
            name = data[e:e + 8].rstrip(b"\0").decode("ascii", "replace")
        secnum = struct.unpack_from("<h", data, e + 12)[0]
        sclass = data[e + 16]
        naux = data[e + 17]
        if secnum > 0 and sclass in (2, 3) and naux and not name.startswith("."):
            defined_by_section.setdefault(secnum, name)
        symbols.append(name)
        symbols.extend([""] * naux)
        i += 1 + naux

    coff = Coff()
    for s in range(nsec):
        h = 20 + optsz + 40 * s
        raw_name = data[h:h + 8].rstrip(b"\0")
        if raw_name.startswith(b"/"):
            name = read_str(strtab + int(raw_name[1:].decode("ascii")))
        else:
            name = raw_name.decode("ascii", "replace")
        _vsize, _vaddr, rawsize, rawptr, relptr, _lnptr, nrel, _nln, _chars = struct.unpack_from(
            "<IIIIIIHHI", data, h + 8
        )
        raw = data[rawptr:rawptr + rawsize] if rawptr else b""
        relocs = []
        for r in range(nrel):
            vaddr, symidx, rtype = struct.unpack_from("<IIH", data, relptr + 10 * r)
            relocs.append((vaddr, rtype, symbols[symidx]))
        relocs.sort()
        group = coff.sections.setdefault(name, {})
        key = defined_by_section.get(s + 1, f"<unnamed {s}>")
        while key in group:
            key += "#dup"
        group[key] = Section(name, key, raw, relocs)
    return coff


def compare_section(ours: Section, ref: Section, res: ObjResult) -> None:
    label = f"{ours.name} {ours.key}"
    if len(ours.raw) != len(ref.raw):
        res.issues.append(f"{label}: size {len(ours.raw)} vs {len(ref.raw)}")
        return
    if ours.relocs != ref.relocs:
        if len(ours.relocs) != len(ref.relocs):
            res.issues.append(f"{label}: {len(ours.relocs)} vs {len(ref.relocs)} relocations")
        else:
            first = next(x for x, y in zip(ours.relocs, ref.relocs) if x != y)
            res.issues.append(f"{label}: relocation differs, first {first} vs {ref.relocs[ours.relocs.index(first)]}")
    if ours.raw == ref.raw:
        return
    site_bytes: set[int] = set()
    for off, _rtype, _sym in ours.relocs:
        site_bytes.update(range(off, off + RELOC_SITE_WIDTH))
    for pos, (x, y) in enumerate(zip(ours.raw, ref.raw)):
        if x != y:
            res.diff_bytes += 1
            if pos in site_bytes:
                res.reloc_site_diff_bytes += 1
            else:
                res.other_diff_bytes += 1


def compare_objects(ours_path: Path, ref_path: Path, sections: list[str]) -> ObjResult:
    res = ObjResult(ours_path.name)
    a = parse_coff(ours_path.read_bytes())
    b = parse_coff(ref_path.read_bytes())
    for name in sections:
        da = a.sections.get(name, {})
        db = b.sections.get(name, {})
        leftover_a: list[Section] = []
        leftover_b: list[Section] = []
        for key, sa in da.items():
            if not key.startswith("<") and key in db:
                compare_section(sa, db[key], res)
            else:
                leftover_a.append(sa)
        matched_b = {k for k in db if not k.startswith("<") and k in da}
        leftover_b = [sb for k, sb in db.items() if k not in matched_b]
        # Unnamed or unmatched sections: pair identical content first, then by order for diagnostics.
        pool: dict[tuple, list[Section]] = {}
        for sb in leftover_b:
            pool.setdefault((sb.raw, tuple(sb.relocs)), []).append(sb)
        rest_a = []
        for sa in leftover_a:
            cands = pool.get((sa.raw, tuple(sa.relocs)))
            if cands:
                cands.pop()
            else:


                rest_a.append(sa)
        rest_b = [sb for cands in pool.values() for sb in cands]
        for sa, sb in zip(rest_a, rest_b):
            compare_section(sa, sb, res)
        for sa in rest_a[len(rest_b):]:
            res.issues.append(f"{name} {sa.key}: no match in reference")
        for sb in rest_b[len(rest_a):]:
            res.issues.append(f"{name} {sb.key}: no match in ours")
    return res


def ref_name_for(ours_name: str) -> str:
    if ours_name.endswith(".cpp.obj"):
        return ours_name[: -len(".cpp.obj")] + ".obj"
    return ours_name


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ours", type=Path, default=DEFAULT_OURS, help="directory with CMake .obj files")
    ap.add_argument("--ref", type=Path, required=True, help="directory with reference (VS2003) .obj files")
    ap.add_argument("--sections", default=DEFAULT_SECTIONS, help="comma-separated section names to compare")
    ap.add_argument("--verbose", action="store_true", help="print every object, not only mismatches")
    ap.add_argument("--max-list", type=int, default=40, help="max mismatching objects to list")
    args = ap.parse_args(argv)

    sections = [s.strip() for s in args.sections.split(",") if s.strip()]
    ours_files = sorted(args.ours.glob("*.obj"))
    if not ours_files:
        print(f"no .obj files in {args.ours}", file=sys.stderr)
        return 2

    identical = 0
    mismatched: list[ObjResult] = []
    missing: list[str] = []
    totals = {"diff": 0, "site": 0, "other": 0}
    for ours_path in ours_files:
        ref_path = args.ref / ref_name_for(ours_path.name)
        if not ref_path.exists():
            missing.append(ours_path.name)
            continue
        res = compare_objects(ours_path, ref_path, sections)
        totals["diff"] += res.diff_bytes
        totals["site"] += res.reloc_site_diff_bytes
        totals["other"] += res.other_diff_bytes
        if res.identical:
            identical += 1
            if args.verbose:
                print(f"OK    {res.name}")
        else:
            mismatched.append(res)
            if args.verbose:
                print(f"DIFF  {res.name}")

    compared = identical + len(mismatched)
    print(f"sections: {', '.join(sections)}")
    print(f"objects compared: {compared}  identical: {identical}  mismatched: {len(mismatched)}  no reference: {len(missing)}")
    print(f"differing bytes: {totals['diff']}  at relocation sites: {totals['site']}  elsewhere: {totals['other']}")
    for res in mismatched[: args.max_list]:
        detail = "; ".join(res.issues) if res.issues else f"{res.diff_bytes} bytes ({res.other_diff_bytes} outside relocs)"
        print(f"  {res.name}: {detail}")
    if len(mismatched) > args.max_list:
        print(f"  ... {len(mismatched) - args.max_list} more")
    for name in missing[: args.max_list]:
        print(f"  no reference for {name}")
    return 0 if not mismatched and not missing else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
