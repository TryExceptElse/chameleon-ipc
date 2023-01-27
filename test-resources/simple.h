/** @file
 * Fake boilerplate...
 */
#include <cstddef>
#include <cstdint>
#include <functional>
#include <string>

namespace cipc::example {

// @IPC(Serializable)
enum class Mode {
    Encabulate,
    SideFumble,
    Idle,
};

// @IPC(Callback)
using ModeChangeCallback = std::function<Mode()>;

// @IPC(Interface)
class Component {
  // @IPC(Method)
  virtual std::string name() const;

  // @IPC(Method)
  virtual std::size_t id() const;

  // @IPC(Method)
  virtual Mode current_mode() const;

  // @IPC(Method)
  virtual void noop();

  // @IPC(Method)
  virtual int mode_names(
      std::unordered_map<std::string, Mode> mode_map);

  // @IPC(Method)
  virtual int set_mode(Mode mode);
};

// @IPC(Interface)
class System {
  // @IPC(Method)
  virtual std::vector<Component*> components() const;
};

}  // namespace cipcc::example
