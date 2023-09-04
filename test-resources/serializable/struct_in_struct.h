#include <cstddef>
#include <string>

namespace ns {

// @IPC(Serializable)
struct A {
  std::size_t id;
  std::string name;
};

// @IPC(Serializable)
struct B {
  A a;
};

}  // namespace ns
