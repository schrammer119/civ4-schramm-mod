# ABI Contract Findings

Scope: the ABI between `CvGameCoreDLL.dll`, `Civ4BeyondSword.exe`, and the Python assets for Civilization IV: Beyond the Sword. Runtime and save-game testing are out of scope for now.

## Goal

A pass/fail gate for a recompiled DLL, so that a future compiler upgrade does not break the game. The project build system is out of scope for now.

## Binaries (shipped, Steam install)

Install path: `C:\Program Files (x86)\Steam\steamapps\common\Sid Meier's Civilization IV Beyond the Sword\Beyond the Sword\`

- EXE: `Civ4BeyondSword.exe` at the install root. PE32 i386, linker 7.10 (MSVC 7.1), image base `0x00400000`.
- DLL: `Assets\CvGameCoreDLL.dll`. PE32 i386, linker 7.10 (MSVC 7.1), image base `0x10000000`.
- EXE imports `msvcr71.dll`, `msvcp71.dll`, and `python24.dll` directly.
- DLL imports `boost_python-vc71-mt-1_32.dll`, `msvcp71.dll`, `msvcr71.dll`, and `python24.dll`.
- The EXE does not statically import the DLL. It loads it with `LoadLibraryA` and resolves exports with `GetProcAddress`.

## ABI surface

- C++ classes are exported with `__declspec(dllexport)` (`#define DllExport` in `src/CvGameCoreDLL.h`).
- MSVC decorated names encode the signature and calling convention: `E` = thiscall, `A` = cdecl, `G` = stdcall.
- DLL-to-EXE calls go through abstract interface vtables (`*IFaceBase.h`).
- Python registration entry point: `DLLPublishToPython` (`src/CvDLLPython.cpp`).
- `operator new` and `operator delete` are routed through `gDLL` (`#define gDLL GC.getDLLIFaceNonInl()` in `src/CvGlobals.h`).
- Version handshake string `Verify Version Message, .exe=%s, .dll=%d, python=%d, xml=%d` appears only in the EXE. No matching version function was found in `src/`. Not yet traced.

## Tooling added

- `pixi` `dev` environment: Python 3.15.1, pefile 2024.8.26, capstone 5.0.9. Locked in `pixi.lock`.
- `tests/pe_check.py`: stdlib-only PE checker (machine, linker, exports, imports). `--write` regenerates goldens.
- `tests/abi_contract.py`: stdlib-only contract checker. Checks entry points, vtables, Python class names, and CRT sharing between DLL and EXE. Flags: `--dll`, `--exe` (optional), `--golden-dir`, `--write`.
- `tests/abi/inspect_pe.py`: dev-only inspection with pefile and capstone. Flags: `--file` (repeatable), `--disasm SYMBOL`.
- Goldens under `tests/golden/`:
  - `entry_points.txt` (hand-written): `?DLLPublishToPython@@YAXXZ`, `?getDLLIFaceNonInl@CvGlobals@@QAEPAVCvDLLUtilityIFaceBase@@XZ`
  - `vtables.txt`: 5 vtables. Only slot 0 of `CvDLLEntity` is named (`?setup@CvDLLEntity@@UAEXXZ`). All other slots are `<local>`.
  - `python_classes.txt`: 18 names from a regex (`Cy[A-Z][A-Za-z]{2,}\x00`).
  - `exports.txt` (2432 entries), `imports.txt`, `linker.txt`: from the earlier `pe_check` work.
- CMake (root `CMakeLists.txt`, `tests/CMakeLists.txt`): cache variables `CIV4_CANDIDATE_DLL` and `CIV4_GAME_EXE`. Tests `pe_contract`, `abi_contract`, `pe_check_rejects_non_pe` (WILL_FAIL), `abi_contract_rejects_non_pe` (WILL_FAIL).
- `pixi run test` runs the ctest suite in `build-test`.

## Results

- `abi_contract.py` against the Steam DLL and EXE: exit 0.
  - entry_points: 2 match
  - vtables: 5 match
  - python: 18 match
  - crt: `boost_python-vc71-mt-1_32.dll`, `msvcp71.dll`, `msvcr71.dll`, `python24.dll` shared with EXE
- `pixi run test`: 4/4 passed.
- Negative test (altered vtable count): FAIL, missing 1, extra 1, exit 1.

## Caveats

- The goldens were generated from the shipped DLL with `--write`. Passing against that DLL is expected and is a regression baseline, not proof that the full ABI is met.
- `--write` re-baselines the gate. Any change to `tests/golden/` must be reviewed.
- Vtable slot-order checking is weak. Most slots point to unexported code and are `<local>`.
- The Python class golden is regex-derived and not yet cross-checked against `src/CvDLLPython.cpp`.
- The EXE imports `python24.dll` directly. A Python upgrade requires changing or shimming the EXE's imports. A shim named `python24.dll` does not remove the `msvcr71` load, because the EXE imports `msvcr71` itself.
- A static CRT and a rebuilt Boost against a newer Python are acceptable to the user. Separate heaps are a risk only when C++ objects or raw allocations cross the EXE/DLL boundary and are freed on the other side.
- Passing tests do not show that a DLL is safe. Layout, slot order, the handshake, Python-side behavior, and runtime are not verified.
- The repo build cache (`build/CMakeCache.txt`) uses clang (`clang++-22`), not MSVC 7.1. A clang layout probe would pin clang's layout, not the shipped one.
- The EXE is closed source and cannot be rebuilt.

## Environment notes

- Visual Studio 2022 Community is installed at `C:\Program Files\Microsoft Visual Studio\2022\Community`. `cl.exe` and `dumpbin` are not on PATH.
- `.toolchain/Microsoft Visual C++ Toolkit 2003/` (and `.7z`) and `.toolchain/WindowsSDK/` (and `.7z`) are present. Not yet inspected or used.
- Terminal: PowerShell 5.1. Use `;` rather than `&&`. Assign paths containing `Sid Meier's` to a `$game` variable to avoid quoting problems.
- Temporary files outside the repo: `%TEMP%\abi_neg`, `%TEMP%\abi_preview`. Safe to delete.

## Next steps

1. Reproducibility build: inspect `.toolchain\Microsoft Visual C++ Toolkit 2003\` and confirm `cl.exe` and `link.exe` (MSVC 7.1). Build `src/` with it, using `Python24/` and `Boost-1.32.0/`. Compare the built DLL's exports, vtables, and imports to the shipped DLL. A mismatch means the source and the shipped binary have diverged.
2. Layout probe: compile `sizeof` and `offsetof` checks for classes the EXE uses, with the 2003 toolkit, and compare against the built DLL.
3. Slot order: map every vtable slot to its implementing function, using a map file or symbols from the reproducibility build.
4. Version handshake: trace the EXE's `Verify Version Message` logic and find the DLL's version source.
5. Python class cross-check: grep `src/CvDLLPython.cpp` for `Cy` registrations and compare with `tests/golden/python_classes.txt`.
6. Optional negative tests: missing entry point, changed Python class name, added CRT import.
7. Deferred: runtime and save-game testing.
