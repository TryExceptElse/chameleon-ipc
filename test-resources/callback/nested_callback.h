#include <cstddef>
#include <string>

namespace bar {

class Interface {
  // @IPC(Serializable)
  struct Event {
    std::size_t id;
    std::string name;
  };

  // @IPC(Callback)
  using Callback = std::function<void(Event)>;

  int Method();
};

}  // namespace bar::baz
