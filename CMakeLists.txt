cmake_minimum_required(VERSION 3.20)

# The DLL target is added in the 1:1 rebuild phase.
project(CvGameCoreDLL NONE)

option(CIV4_BUILD_TESTS "Build the ABI contract tests" OFF)

if(CIV4_BUILD_TESTS)
    enable_testing()

    set(CIV4_CANDIDATE_DLL
        "c:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization IV Beyond the Sword/Beyond the Sword/Assets/CvGameCoreDLL.dll"
        CACHE FILEPATH "DLL under test")

    set(CIV4_GAME_EXE
        "c:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization IV Beyond the Sword/Beyond the Sword/Civ4BeyondSword.exe"
        CACHE FILEPATH "Game EXE that consumes the DLL")

    add_subdirectory(tests)
endif()
