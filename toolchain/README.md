# VS2003 Toolchain

This folder holds a self-contained copy of the Visual C++ 7.1 (VS2003) toolchain used for the 1:1 build of `CvGameCoreDLL.dll`. The build reads only from here, not from the Windows SDK or a system Visual Studio install.

## What to copy

Copy the whole `Vc7` folder from the VS2003 installation (usually `C:\Program Files (x86)\Microsoft Visual Studio .NET 2003\Vc7`) into this folder, so the result is `toolchain\Vc7\`.

The build needs these parts of `Vc7`:

- `bin\`: `cl.exe`, `link.exe`, `rc.exe`, `cvtres.exe`, `lib.exe`, `c1.dll`, `c1xx.dll`, `c2.dll`, `dumpbin.exe`, `nmake.exe`
- `include\`: C and C++ standard headers
- `lib\`: `msvcrt.lib`, `libcmt.lib`, and the other CRT libraries
- `atlmfc\include\` and `atlmfc\lib\`: ATL/MFC headers and libraries
- `PlatformSDK\Include\` and `PlatformSDK\Lib\`: the VS2003 Platform SDK (provides `sal.h`, `windows.h`)

## Runtime DLLs

`cl.exe` and `link.exe` will not start without these four DLLs in `toolchain\Vc7\bin\`. Copy them from the VS2003 installation:

- `mspdb71.dll`
- `msobj71.dll`
- `msvcr71.dll`
- `msvcp71.dll`

A process exit code of `-1073741515` (0xC0000135) means one of these is missing.

## Not needed

Do not copy the Windows 10 SDK, Visual Studio 2022, or the older bundled toolkit. The build must not pick up headers or libraries from them.

## Verify

From the repository root, check that `toolchain\Vc7\bin\cl.exe` and `link.exe` run and print their version banner. Then run the configure and build steps from the handoff notes in `.github\phase-c-handoff.md`.
