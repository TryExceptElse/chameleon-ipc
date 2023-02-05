# Enable ExternalProject CMake module
include(ExternalProject)

function(cipc_archive_name ROOT OUT)
    set(
            ${OUT}
            ${CMAKE_STATIC_LIBRARY_PREFIX}${ROOT}${CMAKE_STATIC_LIBRARY_SUFFIX}
            PARENT_SCOPE)
endfunction()

function(create_gtest_target)
    # Set default ExternalProject root directory
    set(EXTERNAL_PROJECT_DIR ${CMAKE_BINARY_DIR}/third_party)
    set_directory_properties(PROPERTIES EP_PREFIX ${EXTERNAL_PROJECT_DIR})

    set(GTEST_SOURCES ${EXTERNAL_PROJECT_DIR}/src/gtest-project)
    set(GTEST_BUILD_DIR ${GTEST_SOURCES}-build)
    cipc_archive_name(gtest GTEST_LIB_NAME)
    cipc_archive_name(gtest_main GTEST_MAIN_NAME)
    set(GTEST_LIB_PATH ${GTEST_BUILD_DIR}/lib/${GTEST_LIB_NAME})
    set(GTEST_MAIN_PATH ${GTEST_BUILD_DIR}/lib/${GTEST_MAIN_NAME})

    # Add gtest
    # http://stackoverflow.com/questions/9689183/cmake-googletest
    ExternalProject_Add(
            gtest-project
            EXCLUDE_FROM_ALL
            GIT_REPOSITORY https://github.com/google/googletest.git
            GIT_TAG v1.13.0
            GIT_SHALLOW TRUE
            # Wrap download, configure and build steps in a script to log output
            LOG_DOWNLOAD ON
            LOG_CONFIGURE ON
            LOG_BUILD ON
            DOWNLOAD_EXTRACT_TIMESTAMP FALSE
            INSTALL_COMMAND ""
            BYPRODUCTS ${GTEST_LIB_PATH} ${GTEST_MAIN_PATH})

    add_library(gtest INTERFACE)
    target_include_directories(
            gtest INTERFACE ${GTEST_SOURCES}/googletest/include)
    target_link_libraries(gtest INTERFACE ${GTEST_LIB_PATH})
    add_dependencies(gtest gtest-project)

    add_library(gtest_main INTERFACE)
    target_link_libraries(gtest_main INTERFACE ${GTEST_MAIN_PATH})
    add_dependencies(gtest_main gtest-project)
endfunction()
