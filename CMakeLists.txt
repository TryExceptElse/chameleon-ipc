# Copyright 2023 TryExceptElse
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject
# to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
cmake_minimum_required(VERSION 3.9)
project(chameleon)

include(cmake/gtest.cmake)

if(NOT CMAKE_RUNTIME_OUTPUT_DIRECTORY)
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
endif()
if(NOT CMAKE_LIBRARY_OUTPUT_DIRECTORY)
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
endif()
if(NOT CMAKE_ARCHIVE_OUTPUT_DIRECTORY)
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
endif()

option(BUILD_TESTS "Build test targets." OFF)

function(cipc_define_library_target)
    add_library(
            cipc
            cipc/serialize.cc
            cipc/service.cc
            cipc/unix_channel.cc)
    target_include_directories(cipc PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
    set_target_properties(cipc PROPERTIES CXX_STANDARD 17)
endfunction()

function(cipc_define_test_target)
    # Prepare tests.
    create_gtest_target()
    if(NOT BUILD_TESTS)
        set(EXCLUDE_OPT EXCLUDE_FROM_ALL)
    endif()
    add_executable(
            cipc-test
            ${EXCLUDE_OPT}
            cipc/msg_test.cc
            cipc/serialize_test.cc)
    target_include_directories(cipc-test PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
    target_link_libraries(cipc-test PUBLIC cipc gtest gtest_main)
    set_target_properties(cipc-test PROPERTIES CXX_STANDARD 17)
endfunction()

cipc_define_library_target()
cipc_define_test_target()
