#include <cstddef>
#include <string>

// @IPC(Serializable)
class Foo {
 public:
  std::size_t id;
  std::string name;
};
