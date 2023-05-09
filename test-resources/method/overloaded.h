#include <cstdint>
#include <string>

// @IPC(Interface)
class Interface {
  // @IPC(Method)
  virtual int Encode(std::string x) const = 0;

  // @IPC(Method)
  virtual int Encode(std::int32_t x) const = 0;
};
