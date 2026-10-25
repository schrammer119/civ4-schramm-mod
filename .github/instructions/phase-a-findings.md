# Phase A Findings: Shipped CvGameCoreDLL.dll

## Executive summary

Phase A is complete. The shipped DLL is a 32-bit Windows x86 build made with the VC7.1 (VS2003) linker. It depends on Python 2.4 and Boost.Python 1.32 (vc71). Its 2432 named exports are all C++ symbols, so any replacement build must reproduce them. The repo's `src/` directory matches the original source (commit `4ad8ead`) after normalizing formatting, so it is the approved build baseline. Source edits are not needed for Phase A.

## Shipped binary

- Location: `Beyond the Sword\Assets\CvGameCoreDLL.dll`
- Size: 4,949,304 bytes
- SHA256: `7F9F23905177396972F87A168EC785F006BE1D5B9FF730484B05C565A9396278`
- PE timestamp: 2009-05-14 14:02:20
- Sections: 5
- Architecture: x86 (PE32), subsystem GUI
- Linker: 7.10 (VC7.1)
- Version resource: FileVersion 3.1.7.0
- Export table name: `CvGameCoreDLL.dll`

## Imports

- `python24.dll`
- `boost_python-vc71-mt-1_32.dll`
- `msvcr71.dll`
- `msvcp71.dll`
- `kernel32.dll`, `user32.dll`, `winmm.dll`

## Exports

- 2432 named exports, all C++ mangled (names start with `?`).
- No C-linkage exports.
- Any rebuild must match these symbols exactly, including calling convention and name mangling.

## Source baseline

- Original source: commit `4ad8ead` ("initial base code commit", flat layout).
- Current `src/` (HEAD `639bf38`, branch `feat/compile`): 198 files, identical to `4ad8ead` after removing comments, line continuations, and whitespace. Zero files differ. Include order is preserved.
- 197 files differ byte-for-byte because of the clang-format pass. The differences are formatting only.
- Restored shipped sources in `Beyond the Sword\CvGameCoreDLL\`: 198 files, same names as `src/`, zero normalized differences.
- `CvGameCoreDLL.vcproj` in the repo root matches the shipped copy, ignoring whitespace.
- Decision: use `src/` as the baseline.

## Runtime check

- Vanilla launch reaches the main menu.
- Log shows `Mod Loaded: none`.
- `PythonErr.log` is empty.
- `CIV Version: 319`, `Save Version: 302`.

## Open items for Phase B

- Phase B (test harness) has not started and needs approval.
- `.github/instructions/build-findings.md` is stale and comes from another project. Do not use it.
- The stale `build/` CMake cache should not be used as a reference.
- The `src/.gitattributes` removal in `639bf38` should be confirmed as intended.
