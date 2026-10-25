# CvGameCoreDLL build notes (clang-cl + CMake/Ninja via pixi)

## Goal
Compile `CvGameCoreDLL.dll` (step 1: compile only). Target install folder: `C:\Program Files (x86)\Steam\steamapps\common\Sid Meier's Civilization IV Beyond the Sword\Beyond the Sword`.

## Facts
- The engine is 32-bit. Python 2.4 and Boost 1.32 (vc71) are 32-bit. Configure fails if the target is not x86.
- `CvGameCoreDLL.vcproj` is the source of truth for defines, includes, and sources.
- `_precompile.cpp` (PCH generator only) and `CvTextScreens.cpp` (not in vcproj) are excluded from the build.
- Compiler: pixi-provided clang-cl 22 with `--target=i686-pc-windows-msvc`.
- clang-cl needs the VS 2022 x86 environment (`vcvarsall.bat x86`) for INCLUDE/LIB.
- `CvGameTextMgr.cpp` is Windows-1252 (no BOM). clang-cl cannot decode it (`-finput-charset` and `/source-charset` are not supported in this clang build). CMake transcodes it to UTF-8 in `build-win32\utf8-sources` using [cmake/transcode-cp1252.ps1](../cmake/transcode-cp1252.ps1).

## Build command
```
cmd /c "call "<vcvarsall.bat> x86 && cd /d C:\git\civ4-schramm-mod && pixi run cmake -S . -B build-win32 -G Ninja && pixi run cmake --build build-win32 -- -k 0"
```
- Redirect output to `build-win32\build.log`. Check the log for `error:` lines and `FAILED:` counts. The cmd exit code can be 0 even when compilation fails.
- A full build takes longer than 2 minutes. Run it without a short timeout.
- PowerShell 5.1 writes `>` redirects as UTF-16. Use `Get-Content` or `Select-String` to read the log.

## Compile fixes applied
| Issue | Fix | Where |
|---|---|---|
| `##` token pastes in `CvArtFileMgr.h` | `-Wno-invalid-token-paste` | CMakeLists.txt |
| `<hash_map>` deprecation gate | `_SILENCE_STDEXT_HASH_DEPRECATION_WARNINGS` | CMakeLists.txt |
| Exceptions used by Boost.Python | `/EHsc` | CMakeLists.txt |
| MSVC for-loop scoping (`i`, `iK`, `iI` used after the loop) | `/Zc:forScope-` | CMakeLists.txt |
| `CvWString` passed through varargs | `-Wno-non-pod-varargs` | CMakeLists.txt |
| cp1252 literals in `CvGameTextMgr.cpp` | Build-time transcode to UTF-8 | CMakeLists.txt, cmake/transcode-cp1252.ps1 |
| `std::list<...>::_Alloc::size_type` (MSVC STL internal) | `size_t` (same type on 32-bit) | CvPlayer.cpp, CvGame.cpp |
| Loop variables used after their `for` (MSVC for-scope leakage); `/Zc:forScope-` is NOT honored by clang-cl | Hoisted declarations / `for (int ...)` headers | CvGame.cpp, CvGameTextMgr.cpp, CvUnitAI.cpp |
| `CvUnitAI::AI_spreadCorporation` reads loop index after `break` | `int iI;` hoisted, keeps value | CvUnitAI.cpp |
| `CvGameInterface.cpp` conscript flyout read leaked `iI` (last Hurry loop index) | Replaced with `GC.getNumHurryInfos()`, same value. Looks like a latent bug, review later | CvGameInterface.cpp |
| Boost.Python `typeid` on incomplete `CyPlot`/`CyUnit`/`CyDeal` | Include full Cy*.h in the failing TUs | CyGameInterface.cpp, CyGameTextMgrInterface.cpp, CyMapGeneratorInterface.cpp, CyCityInterface1.cpp |
| Ternary of `void` and `NULL` | `if` statement | CyPlayer.cpp (`disbandUnit`) |
| Ternary of `CvWString` and `std::wstring` | `std::wstring(...)` on the left operand | CyPlayer.cpp |
| Ternary of `const wchar_t*` and `CvWString` | `CvWString(...)` on the left operand (14 sites) | CvDLLWidgetData.cpp (Civilopedia) |
| `const char[2]` passed as `void*` | C-style `(void*)` cast | FDialogTemplate.cpp |

## Status
- Compile: 0 errors. Link: `build-win32\CvGameCoreDLL.dll` produced (step 1 done).
- Not done: copying the DLL to the game folder, and runtime testing (out of scope for step 1).
- Warnings are not triaged (deprecated CRT/`stricmp`, nonportable include case in `AI_defines.h` and `CvDllEntity.h`).

## Open items
- `-Wno-non-pod-varargs` hides `CvWString` passed through varargs. Verify the generated code matches MSVC behavior before relying on those calls.
- The `CvGameInterface.cpp` conscript flyout value above should be reviewed against intent.
