cmake_minimum_required(VERSION 3.15)
project(pygamehack_tests)

set(CMAKE_CXX_STANDARD 17)

set(ARCH_SUFFIX "-64")
if(${CMAKE_GENERATOR_PLATFORM} STREQUAL Win32)
    set(ARCH_SUFFIX "-32")
endif()

add_custom_target(ALL)


function(add_test_program PROGRAM_NAME PROGRAM_SOURCE)
    
    add_executable(${PROGRAM_NAME} ${PROGRAM_SOURCE})

    target_compile_definitions(${PROGRAM_NAME} PRIVATE -DARCH_SUFFIX="${ARCH_SUFFIX}")

    file(REMOVE "${CMAKE_CURRENT_SOURCE_DIR}/MarkerAddress${ARCH_SUFFIX}.txt")

    ADD_CUSTOM_COMMAND(TARGET ${PROGRAM_NAME} POST_BUILD
                    COMMAND ${CMAKE_COMMAND} -E copy
                        $<TARGET_FILE:${PROGRAM_NAME}>
                        "${CMAKE_CURRENT_SOURCE_DIR}/${PROGRAM_NAME}${ARCH_SUFFIX}.exe")

    add_dependencies(ALL ${PROGRAM_NAME})

endfunction()


add_test_program(TestProgram TestProgram2.cpp)
