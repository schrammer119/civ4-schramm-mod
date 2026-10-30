# CvGameCoreDLL.dll: Shipped, VS2003, and CMake Findings

Status: working reference for ABI and DLL test work. This records what has been measured, what is explained, and what remains open. It does not claim byte-identical output.

## 1. Artifacts

| Label | Path | Size (bytes) | SHA-256 (prefix) | Notes |
|---|---|---|---|---|
| Shipped | `Steam ... Beyond the Sword\Beyond the Sword\Assets\CvGameCoreDLL.dll` | 4,949,304 | 7F9F239051773969 | FileVersion 3.1.7.0; carries an Authenticode security directory |
| VS2003 | `Steam ... Beyond the Sword\Beyond the Sword\CvGameCoreDLL\Final Release\CvGameCoreDLL.dll` | 4,943,872 | D415F60DDECD9644 | Built with VS2003 (cl 13.10.3077, link 7.10.3077) from the 198-file source copy |
| CMake | `build/final-release-vc7/CvGameCoreDLL.dll` | 4,943,872 | 476D6B5457056EF7 | CMake 4.4.4 + Ninja 1.13.2, toolchain `cmake/vc71-toolkit.cmake`, preset `final-release-vc7` |

Do not use the root `Assets\CvGameCoreDLL.dll` in the Civ4 base install (3,716,672 bytes, version 1.0.0.1). It is a different DLL.

PE timestamps for the VS2003 and CMake builds reflect the build machine clock (2026). Do not use them as evidence.

## 2. Object code equivalence (build inputs)

- 99 objects compared with [tools/compare_obj.py](tools/compare_obj.py) against the VS2003 `.obj` files: `.text`, `.data`, `.rdata`, with 4-byte relocation sites masked.
- 98 of 99 are identical.
- The exception is `CvGameCoreDLL.cpp.obj`. Its only difference is the `__FILE__` string, which contains the build path. This is a path exception, not a code difference.

## 3. Exports (ABI surface)

- Shipped, VS2003, and CMake each export 2,432 names with ordinals.
- Names and ordinals are identical across all three.
- Shipped export function RVAs are identical to VS2003 for all 2,432.
- CMake export RVAs differ from VS2003 for 1,692 exports. The deltas are -32, -48, -96, and -128 bytes, all inside `.text`. This is code placement (COMDAT ordering), not a different export set.

## 4. Imports

- Each binary imports 157 functions from 6 DLLs.
- The function sets are identical across shipped, VS2003, and CMake.

| DLL | Functions |
|---|---|
| boost_python-vc71-mt-1_32.dll | 52 |
| msvcp71.dll | 42 |
| msvcr71.dll | 42 |
| python24.dll | 17 |
| winmm.dll | 3 |
| user32.dll | 1 |

Counts checked against the `dumpbin /imports` dump (`build/experiments/3way/vs2003.imports.txt`) and by `tools/dll_compare.py`.

## 5. Sections

| Section | VirtualSize Shipped | VirtualSize VS2003 | VirtualSize CMake | Raw size (all three) |
|---|---|---|---|---|
| .text | 0x3676F1 | 0x3676F1 | 0x3676F1 | 0x368000 |
| .rdata | 0x0AD58E | 0x0AD5EE | 0x0AD5AE | 0x0AE000 |
| .data | 0x04529C | 0x04529C | 0x04529C | 0x03C000 |
| .rsrc | 0x0004F8 | 0x0004F8 | 0x0004F8 | 0x001000 |
| .reloc | 0x062CF2 | 0x062CF2 | 0x062CF2 | 0x063000 |

Virtual addresses and raw pointers are identical in all three.

### 5.1 Shipped vs VS2003

- File size gap of 5,432 bytes (0x1538) is fully explained. The shipped file is the VS2003 image followed by a 5,432-byte Authenticode blob at file offset 0x4B7000, which is exactly the VS2003 file size. The security data directory entry points to that blob.
- Header differences: timestamp, checksum (0x004C514C in shipped, 0 in VS2003), security directory added, export/import directory RVAs shifted by -96, and base-relocation directory size differs by 20 bytes. These are consistent with the post-link changes and the `.rdata` shift below.
- `.data` and `.rsrc`: byte-identical (0 differing bytes).
- `.text`: 3,126 bytes differ. All of them sit on absolute-address (relocation) fields. 2,016 of those fields point into `.rdata` and are exactly 96 bytes lower in the shipped image. This is the `.rdata` shift below, carried into `.text`. About 1,110 differing fields remain unclassified (integer constants or other non-RVA values, 610 + 308 + 55 + 137 sites).
- `.rdata`: shifted by 96 bytes before the export directory. Content after the shift is misaligned, so most of the 292,725 differing bytes are a consequence of that shift, not new content. The shift cause is not identified.

### 5.2 CMake vs VS2003

- `.text`: same VirtualSize, but 2,276,582 raw bytes differ. This is expected because COMDAT placement moves functions and rel32/absolute fields change. Function-level equivalence is covered by section 2 (object code) and section 3 (export RVA deltas).
- `.rdata`: VirtualSize 64 bytes smaller (0x0AD5AE vs 0x0AD5EE). Shift is 64 bytes at the same point as the shipped shift of 96 bytes. The 32-byte difference between shipped and CMake is consistent with path-length string differences in `.rdata` (for example, `__FILE__`). This is a hypothesis and not yet verified.
- `.data`: 15,446 raw bytes differ.
  - 1,833 are on relocation sites.
  - 13,613 are not. Of 15,757 aligned 16-byte chunks without relocation sites, 936 do not appear anywhere in VS2003 `.data`. The rest match VS2003 content at a different offset, so most of the difference is placement. The 936 unmatched chunks are unexplained.
- `.reloc`: differs in layout because the section moves with `.rdata`. Not separately verified.

## 6. Runtime smoke test scope

- Main menu reached; `Mod Loaded: none`; `PythonErr.log` empty; `CIV Version: 319`; `Save Version: 302`.
- A new game started, handful of turns played.
- Scope is narrow: it covers only code reached on that path. It does not validate gameplay, saves beyond the version check, or the modded paths.

## 7. Open items

1. Explain the 1,110 unclassified `.text` relocation fields in the shipped DLL.
2. Explain the 936 unmatched CMake `.data` chunks.
3. Identify the cause of the `.rdata` shift (shipped 96 bytes, CMake 64 bytes). Candidate: path-length strings. Verify with a `/MAP` comparison.
4. The `/GS-` vs default codegen mismatch is unresolved. The project vcproj sets `BufferSecurityCheck=FALSE`, but VS2003 matches the default build.
5. LNK4218 (`cmake_pch.cxx.obj`) and LNK4089 (`KERNEL32` references discarded by `/OPT:REF`) are not yet assessed. LNK4089 also appears in the VS2003 build.
6. Header field-by-field verification is pending beyond the differences listed in 5.1.

## 8. Claim wording until open items close

- Object code: 98 of 99 identical, the exception is `__FILE__` (build path).
- Exports: identical names and ordinals across shipped, VS2003, and CMake.
- Imports: identical function sets across all three.
- Shipped vs VS2003: `.data` and `.rsrc` identical; `.text` differs only in absolute-address fields; the 5,432-byte size gap is the Authenticode blob.
- CMake vs VS2003: `.text` layout differs (placement only at the export level); `.data` and `.rdata` differ by placement and shifts, with residue listed above.
- Not byte-identical. Functionally equivalent within the scope of the smoke test and the export/import matching above.

## 9. Seed list for ABI tests

- Export names and ordinals (2,432 entries): `build/experiments/3way/vs2003.exports.txt`.
- Import set (157 functions across 6 DLLs): `build/experiments/3way/*.imports.txt`.
- Struct and vtable layout: derive from the object files (identity verified by section 2).
- Smoke-test checks: main menu reached, version strings, empty Python error log.

## 10. Reproduction

- Object code: `pixi run -e dev python tools/compare_obj.py` (see [tools/compare_obj.py](tools/compare_obj.py)).
- DLL comparison (headers, sections, exports, imports, byte differences, relocation-site classification): `pixi run -e dev python tools/dll_compare.py REFERENCE.dll OTHER.dll [OTHER2.dll ...] [--runs N] [--pointer-deltas]` (see [tools/dll_compare.py](tools/dll_compare.py)). Deltas are OTHER minus REFERENCE.
- Relink with a map file: `pixi run -e dev python tools/link_with_map.py LINK_CMD.txt OUT_DIR` (see [tools/link_with_map.py](tools/link_with_map.py)).
- Three-way dumps for the seed list: `toolchain/Vc7/bin/dumpbin.exe /exports|/imports|/headers` into `build/experiments/3way/`.
