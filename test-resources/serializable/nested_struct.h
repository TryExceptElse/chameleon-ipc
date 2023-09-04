#include <cstddef>
#include <string>

namespace bar {

class Interface {
  // @IPC(Serializable)
  struct Foo {
    std::size_t id;
    std::string name;
  };

  int Method();
};

}  // namespace bar::baz
