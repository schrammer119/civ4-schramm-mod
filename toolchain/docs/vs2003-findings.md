## C++ Compile

command line options:
```
/O2 /G7 /I "Boost-1.32.0\include" /I "Python24\include" /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_USRDLL" /D "CVGAMECOREDLL_EXPORTS" /D "FINAL_RELEASE" /D "_WINDLL" /D "_MBCS" /FD /EHsc /MD /GR /Yu"CvGameCoreDLL.h" /Fp"Final Release/CvGameCoreDLL.pch" /Fo"Final Release/" /Fd"Final Release/vc70.pdb" /W3 /nologo /c /Zi /Gd /TP
```

## Linker

linker command line options:
```
/OUT:"../Beyond the Sword/Assets/CvGameCoreDLL.dll" /INCREMENTAL:NO /NOLOGO /LIBPATH:"Python24\libs" /LIBPATH:"boost-1.32.0\libs\\" /DLL /DEBUG /PDB:"Final Release/CvGameCoreDLL.pdb" /SUBSYSTEM:WINDOWS /LARGEADDRESSAWARE /OPT:REF /OPT:ICF /IMPLIB:"Final Release/CvGameCoreDLL.lib" /MACHINE:X86 boost_python-vc71-mt-1_32.lib  winmm.lib  kernel32.lib user32.lib gdi32.lib winspool.lib comdlg32.lib advapi32.lib shell32.lib ole32.lib oleaut32.lib uuid.lib odbc32.lib odbccp32.lib ".\Boost-1.32.0\libs\boost_python-vc71-mt-1_32.lib"
```

## Resources

resource command line options:
```
/fo"Final Release/CvGameCoreDLL.res"
```