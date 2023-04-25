#include <string>

// @IPC(Interface)
class Interface {
  // @IPC(Method)
  virtual int DoTheThing(std::string foo, int baz) const = 0;
};
