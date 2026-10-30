cmake_minimum_required(VERSION 3.20)

# Runtime from CMAKE_MSVC_RUNTIME_LIBRARY only; without it CMake adds /MDd to the compile line.
cmake_policy(SET CMP0091 NEW)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")

project(CVGAMECOREDLL NONE)

# 1:1 rebuild: compiles CvGameCoreDLL.dll with the VC7.1 toolkit.
# Configure with -DCMAKE_TOOLCHAIN_FILE=cmake/vc71-toolkit.cmake.
option(CIV4_BUILD_DLL "Build CvGameCoreDLL.dll (Final Release flags of CvGameCoreDLL.vcproj)" OFF)

if(CIV4_BUILD_DLL)
    enable_language(CXX)
    enable_language(RC)

    # Drop CMake's default flags (Debug /Od /GZ /MDd, /GX, _DEBUG, RC -D_DEBUG) so that
    # only the Final Release set below reaches the compiler.
    foreach(_lang CMAKE_C CMAKE_CXX CMAKE_RC)
        foreach(_cfg "" _DEBUG _RELEASE _MINSIZEREL _RELWITHDEBINFO)
            set(${_lang}_FLAGS${_cfg} "")
        endforeach()
    endforeach()

    # cmcldeps would preprocess the .rc with the 2003 cl, which cannot read the newer SDK headers.
    set(CMAKE_NINJA_CMCLDEPS_RC 0)

    set(CIV4_BOOST_DIR "${CMAKE_SOURCE_DIR}/src/Boost-1.32.0")
    set(CIV4_PYTHON_DIR "${CMAKE_SOURCE_DIR}/src/Python24")
    set(CIV4_VC71_DIR "${CMAKE_SOURCE_DIR}/toolchain/Vc7")
    set(CIV4_ATL_DIR "${CMAKE_SOURCE_DIR}/toolchain/Vc7/atlmfc")
    set(CIV4_SDK_DIR "${CMAKE_SOURCE_DIR}/toolchain/Vc7/PlatformSDK")

    # Explicit list in CvGameCoreDLL.vcproj order (link order matches the VS2003 build).
    set(CIV4_SRC "${CMAKE_SOURCE_DIR}/src")
    set(CIV4_DLL_SOURCES
        "${CIV4_SRC}/_precompile.cpp"
        "${CIV4_SRC}/CvArea.cpp"
        "${CIV4_SRC}/CvArtFileMgr.cpp"
        "${CIV4_SRC}/CvCity.cpp"
        "${CIV4_SRC}/CvCityAI.cpp"
        "${CIV4_SRC}/CvDeal.cpp"
        "${CIV4_SRC}/CvDiploParameters.cpp"
        "${CIV4_SRC}/CvDLLButtonPopup.cpp"
        "${CIV4_SRC}/CvDLLEntity.cpp"
        "${CIV4_SRC}/CvDLLPython.cpp"
        "${CIV4_SRC}/CvDllPythonEvents.cpp"
        "${CIV4_SRC}/CvDllTranslator.cpp"
        "${CIV4_SRC}/CvDLLWidgetData.cpp"
        "${CIV4_SRC}/CvEventReporter.cpp"
        "${CIV4_SRC}/CvFractal.cpp"
        "${CIV4_SRC}/CvGame.cpp"
        "${CIV4_SRC}/CvGameAI.cpp"
        "${CIV4_SRC}/CvGameCoreDLL.cpp"
        "${CIV4_SRC}/CvGameCoreUtils.cpp"
        "${CIV4_SRC}/CvGameInterface.cpp"
        "${CIV4_SRC}/CvGameTextMgr.cpp"
        "${CIV4_SRC}/CvGlobals.cpp"
        "${CIV4_SRC}/CvHallOfFameInfo.cpp"
        "${CIV4_SRC}/CvInfos.cpp"
        "${CIV4_SRC}/CvInfoWater.cpp"
        "${CIV4_SRC}/CvInitCore.cpp"
        "${CIV4_SRC}/CvMap.cpp"
        "${CIV4_SRC}/CvMapGenerator.cpp"
        "${CIV4_SRC}/CvMessageControl.cpp"
        "${CIV4_SRC}/CvMessageData.cpp"
        "${CIV4_SRC}/CvPlayer.cpp"
        "${CIV4_SRC}/CvPlayerAI.cpp"
        "${CIV4_SRC}/CvPlot.cpp"
        "${CIV4_SRC}/CvPlotGroup.cpp"
        "${CIV4_SRC}/CvPopupInfo.cpp"
        "${CIV4_SRC}/CvPopupReturn.cpp"
        "${CIV4_SRC}/CvRandom.cpp"
        "${CIV4_SRC}/CvReplayInfo.cpp"
        "${CIV4_SRC}/CvReplayMessage.cpp"
        "${CIV4_SRC}/CvSelectionGroup.cpp"
        "${CIV4_SRC}/CvSelectionGroupAI.cpp"
        "${CIV4_SRC}/CvStatistics.cpp"
        "${CIV4_SRC}/CvStructs.cpp"
        "${CIV4_SRC}/CvTalkingHeadMessage.cpp"
        "${CIV4_SRC}/CvTeam.cpp"
        "${CIV4_SRC}/CvTeamAI.cpp"
        "${CIV4_SRC}/CvUnit.cpp"
        "${CIV4_SRC}/CvUnitAI.cpp"
        "${CIV4_SRC}/CvXMLLoadUtility.cpp"
        "${CIV4_SRC}/CvXMLLoadUtilityGet.cpp"
        "${CIV4_SRC}/CvXMLLoadUtilityInit.cpp"
        "${CIV4_SRC}/CvXMLLoadUtilitySet.cpp"
        "${CIV4_SRC}/FAssert.cpp"
        "${CIV4_SRC}/FDialogTemplate.cpp"
        "${CIV4_SRC}/CyArgsList.cpp"
        "${CIV4_SRC}/CyArea.cpp"
        "${CIV4_SRC}/CyAreaInterface.cpp"
        "${CIV4_SRC}/CyArtFileMgr.cpp"
        "${CIV4_SRC}/CyArtFileMgrInterface.cpp"
        "${CIV4_SRC}/CyCityInterface1.cpp"
        "${CIV4_SRC}/CyEnumsInterface.cpp"
        "${CIV4_SRC}/CyGameCoreUtils.cpp"
        "${CIV4_SRC}/CyGameCoreUtilsInterface.cpp"
        "${CIV4_SRC}/CyGameInterface.cpp"
        "${CIV4_SRC}/CyGameTextMgr.cpp"
        "${CIV4_SRC}/CyGameTextMgrInterface.cpp"
        "${CIV4_SRC}/CyGlobalContext.cpp"
        "${CIV4_SRC}/CyGlobalContextInterface1.cpp"
        "${CIV4_SRC}/CyGlobalContextInterface2.cpp"
        "${CIV4_SRC}/CyGlobalContextInterface3.cpp"
        "${CIV4_SRC}/CyGlobalContextInterface4.cpp"
        "${CIV4_SRC}/CyHallOfFameInfo.cpp"
        "${CIV4_SRC}/CyHallOfFameInterface.cpp"
        "${CIV4_SRC}/CyInfoInterface1.cpp"
        "${CIV4_SRC}/CyInfoInterface2.cpp"
        "${CIV4_SRC}/CyInfoInterface3.cpp"
        "${CIV4_SRC}/CyMap.cpp"
        "${CIV4_SRC}/CyMapGenerator.cpp"
        "${CIV4_SRC}/CyMapGeneratorInterface.cpp"
        "${CIV4_SRC}/CyMapInterface.cpp"
        "${CIV4_SRC}/CyMessageControl.cpp"
        "${CIV4_SRC}/CyMessageControlInterface.cpp"
        "${CIV4_SRC}/CyPlayer.cpp"
        "${CIV4_SRC}/CyPlayerInterface1.cpp"
        "${CIV4_SRC}/CyPlayerInterface2.cpp"
        "${CIV4_SRC}/CyPlot.cpp"
        "${CIV4_SRC}/CyPlotInterface1.cpp"
        "${CIV4_SRC}/CyRandomInterface.cpp"
        "${CIV4_SRC}/CyReplayInfo.cpp"
        "${CIV4_SRC}/CySelectionGroup.cpp"
        "${CIV4_SRC}/CySelectionGroupInterface.cpp"
        "${CIV4_SRC}/CyStructsInterface1.cpp"
        "${CIV4_SRC}/CyTeam.cpp"
        "${CIV4_SRC}/CyTeamInterface.cpp"
        "${CIV4_SRC}/CyUnit.cpp"
        "${CIV4_SRC}/CyUnitInterface1.cpp"
        "${CIV4_SRC}/CyCity.cpp"
        "${CIV4_SRC}/CyDeal.cpp"
        "${CIV4_SRC}/CyGame.cpp")

    add_library(CVGAMECOREDLL SHARED ${CIV4_DLL_SOURCES} src/CvGameCoreDLL.rc)
    set_target_properties(CVGAMECOREDLL PROPERTIES OUTPUT_NAME CvGameCoreDLL)

    # VS2003-style PCH: _precompile.cpp creates it (/Yc), every other source uses it (/Yu).
    set(CIV4_PCH_FILE "${CMAKE_CURRENT_BINARY_DIR}/CvGameCoreDLL.pch")
    set(CIV4_PCH_CREATOR "${CMAKE_SOURCE_DIR}/src/_precompile.cpp")
    set(CIV4_PCH_CREATOR_OBJ "${CMAKE_CURRENT_BINARY_DIR}/CMakeFiles/CVGAMECOREDLL.dir/src/_precompile.cpp.obj")
    set(CIV4_PCH_USERS ${CIV4_DLL_SOURCES})
    list(REMOVE_ITEM CIV4_PCH_USERS "${CIV4_PCH_CREATOR}")
    set_source_files_properties(${CIV4_PCH_USERS} PROPERTIES
        COMPILE_OPTIONS "/YuCvGameCoreDLL.h;/Fp${CIV4_PCH_FILE}"
        OBJECT_DEPENDS "${CIV4_PCH_CREATOR_OBJ}")
    set_source_files_properties("${CIV4_PCH_CREATOR}" PROPERTIES
        COMPILE_OPTIONS "/YcCvGameCoreDLL.h;/Fp${CIV4_PCH_FILE}")

    target_include_directories(CVGAMECOREDLL PRIVATE
        "${CMAKE_SOURCE_DIR}/src"
        "${CIV4_BOOST_DIR}/include"
        "${CIV4_PYTHON_DIR}/include"
        "${CIV4_VC71_DIR}/include"
        "${CIV4_ATL_DIR}/include"
        "${CIV4_SDK_DIR}/Include")

    # Resource compiler needs resource.h (src) and AFXRES.H (atlmfc include).
    set_source_files_properties(src/CvGameCoreDLL.rc PROPERTIES
        INCLUDE_DIRECTORIES "${CMAKE_SOURCE_DIR}/src;${CIV4_ATL_DIR}/include")

    # Compile definitions and options, per VS2003 CvGameCoreDLL.vcproj
    target_compile_definitions(CVGAMECOREDLL
        PRIVATE
        WIN32
        NDEBUG
        _WINDOWS
        _USRDLL
        FINAL_RELEASE
        _WINDLL
        _MBCS
    )
    target_compile_options(CVGAMECOREDLL
        PRIVATE
        /nologo
        /O2
        /G7
        /FD
        /EHsc
        /GR
        /W3
        /Zi
        /Gd

        # /Oy
        # /Oi
        # /GL
        # /Gy
    )

    # Linker, per the same config:
    target_link_options(CVGAMECOREDLL
        PRIVATE
        /NOLOGO
        /DLL
        /DEBUG
        /SUBSYSTEM:WINDOWS
        /LARGEADDRESSAWARE
        /OPT:REF
        /OPT:ICF
        /MACHINE:X86
        "/LIBPATH:${CIV4_PYTHON_DIR}/libs"
        "/LIBPATH:${CIV4_BOOST_DIR}/libs"
        "/LIBPATH:${CIV4_VC71_DIR}/lib"
        "/LIBPATH:${CIV4_ATL_DIR}/lib"
        "/LIBPATH:${CIV4_SDK_DIR}/Lib"
    )
    target_link_libraries(CVGAMECOREDLL
        PRIVATE
        boost_python-vc71-mt-1_32.lib
        winmm.lib
        "${CMAKE_SOURCE_DIR}\\src\\Boost-1.32.0\\libs\\boost_python-vc71-mt-1_32.lib"
    )
endif()
