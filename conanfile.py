from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout


class CipcRecipe(ConanFile):
    """Conan package recipe for the chameleon IPC library"""
    name = 'cipc'
    version = '0.0.1'
    license = 'MIT'
    author = 'TryExceptElse'
    url = 'https://github.com/TryExceptElse/chameleon-ipc'
    description = 'C++ IPC/RPC system where the IDL is annotated C++'
    topics = 'IPC', 'C++', 'IDL'

    settings = 'os', 'compiler', 'build_type', 'arch'
    options = {'shared': [True, False], 'fPIC': [True, False]}
    default_options = {'shared': False, 'fPIC': True}

    exports_sources = 'CMakeLists.txt', 'cmake/*', 'cipc/*'

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={'BUILD_TESTS': 'OFF'})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = 'cipc'
