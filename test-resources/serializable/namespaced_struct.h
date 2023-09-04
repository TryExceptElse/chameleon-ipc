#include <cstddef>
#include <string>

namespace bar::baz {

// @IPC(Serializable)
struct Foo {
  std::size_t id;
  std::string name;
};

}  // namespace bar::baz
