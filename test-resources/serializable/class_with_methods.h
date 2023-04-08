#include <cstddef>
#include <string>

// @IPC(Serializable, auto=False)
class Foo {
 public:
  Foo() : id(1), name("foo") {}

  Foo(const Foo& other) = default;
  Foo(Foo&& other) = default;

  Foo& operator=(const Foo& other) = default;
  Foo& operator=(Foo&& other) = default;

  auto full_name() const -> std::string {
    return name + std::to_string(id);
  }

  // @IPC(Field)
  std::size_t id;
  // @IPC(Field)
  std::string name;
};
