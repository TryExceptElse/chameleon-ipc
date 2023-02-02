# Enable ExternalProject CMake module
include(ExternalProject)

function(collect_gtest)
    # Set default ExternalProject root directory
    set(EP_DIR ${CMAKE_BINARY_DIR}/third_party)
    set_directory_properties(PROPERTIES EP_PREFIX ${EP_DIR})

    # Add gtest
    # http://stackoverflow.com/questions/9689183/cmake-googletest
    ExternalProject_Add(
            gtest-project
            GIT_REPOSITORY https://github.com/google/googletest.git
            GIT_TAG v1.13.0
            # Wrap download, configure and build steps in a script to log output
            LOG_DOWNLOAD ON
            LOG_CONFIGURE ON
            LOG_BUILD ON
            DOWNLOAD_EXTRACT_TIMESTAMP FALSE
            INSTALL_COMMAND "")
    set(GTEST_DIR ${EP_DIR}/src/gtest-project)
    if(EXISTS ${GTEST_DIR})
        add_subdirectory(${GTEST_DIR} EXCLUDE_FROM_ALL)
    endif()
endfunction()
