#include <cstddef>
#include <string>

// @IPC(Serializable)
struct Foo {
  std::string name = "A complex name;  // @IPC(Serializable)";
  std::size_t id = 0;
};
