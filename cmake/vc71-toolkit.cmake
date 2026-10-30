# Toolchain file: Microsoft Visual C++ Toolkit 2003 (cl 13.10, link 7.10)
# plus VS2003 Platform SDK, ATL/MFC headers and rc.exe, all taken from toolchain/.
# Used by the 1:1 rebuild only; the modern build (Phase D) uses a different file.

set(CIV4_TOOLKIT_ROOT "${CMAKE_CURRENT_LIST_DIR}/../toolchain")
set(CIV4_VC71_DIR "${CIV4_TOOLKIT_ROOT}/Vc7")
set(CIV4_SDK_DIR "${CIV4_VC71_DIR}/PlatformSDK")
set(CIV4_ATL_DIR "${CIV4_VC71_DIR}/atlmfc")
set(CIV4_RC_DIR "${CIV4_VC71_DIR}/bin")

set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86)

# Same search paths vcvars32.bat would provide (VC, then ATL/MFC, then the Platform SDK).
set(ENV{INCLUDE} "${CIV4_VC71_DIR}/include;${CIV4_ATL_DIR}/include;${CIV4_SDK_DIR}/Include")
set(ENV{LIB} "${CIV4_VC71_DIR}/lib;${CIV4_ATL_DIR}/lib;${CIV4_SDK_DIR}/Lib")

set(CMAKE_C_COMPILER "${CIV4_VC71_DIR}/bin/cl.exe")
set(CMAKE_CXX_COMPILER "${CIV4_VC71_DIR}/bin/cl.exe")
set(CMAKE_LINKER "${CIV4_VC71_DIR}/bin/link.exe")
set(CMAKE_RC_COMPILER "${CIV4_RC_DIR}/rc.exe")

# Toolkit 2003 ships no lib.exe; the DLL target never builds a static library.
set(CMAKE_C_CREATE_STATIC_LIBRARY "")
set(CMAKE_CXX_CREATE_STATIC_LIBRARY "")
