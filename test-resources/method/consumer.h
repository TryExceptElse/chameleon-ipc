#include <cstdint>

// @IPC(Interface)
class Interface {
  // @IPC(Method)
  virtual void DoTheThing(std::int32_t foo) const = 0;
};
