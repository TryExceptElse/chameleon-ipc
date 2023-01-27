#include <cstddef>
#include <string>

struct Foo {
  std::string name = "A complex name; // @IPC(Serializable)";
  std::size_t id = 0;
};
