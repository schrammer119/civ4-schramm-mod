find_package(Python3 REQUIRED COMPONENTS Interpreter)

add_test(NAME pe_contract
    COMMAND Python3::Interpreter ${CMAKE_CURRENT_SOURCE_DIR}/pe_check.py
            --dll ${CIV4_CANDIDATE_DLL}
            --golden-dir ${CMAKE_CURRENT_SOURCE_DIR}/golden)

add_test(NAME abi_contract
    COMMAND Python3::Interpreter ${CMAKE_CURRENT_SOURCE_DIR}/abi_contract.py
            --dll ${CIV4_CANDIDATE_DLL}
            --exe ${CIV4_GAME_EXE}
            --golden-dir ${CMAKE_CURRENT_SOURCE_DIR}/golden)

# ABI self-check: a non-PE input must make the contract checker fail.
add_test(NAME abi_contract_rejects_non_pe
    COMMAND Python3::Interpreter ${CMAKE_CURRENT_SOURCE_DIR}/abi_contract.py
            --dll ${CMAKE_CURRENT_SOURCE_DIR}/pe_check.py
            --golden-dir ${CMAKE_CURRENT_SOURCE_DIR}/golden)
set_tests_properties(abi_contract_rejects_non_pe PROPERTIES WILL_FAIL TRUE)

# Harness self-check: a non-PE input must make the checker fail.
add_test(NAME pe_check_rejects_non_pe
    COMMAND Python3::Interpreter ${CMAKE_CURRENT_SOURCE_DIR}/pe_check.py
            --dll ${CMAKE_CURRENT_SOURCE_DIR}/pe_check.py
            --golden-dir ${CMAKE_CURRENT_SOURCE_DIR}/golden)
set_tests_properties(pe_check_rejects_non_pe PROPERTIES WILL_FAIL TRUE)
