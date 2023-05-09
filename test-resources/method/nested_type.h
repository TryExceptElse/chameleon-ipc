#include <string>

namespace ns1 {
namespace ns2 {

// @IPC(Interface)
class Interface {
  // @IPC(Serializable)
  struct Conf {
    std::string name;
    int dev_id;
  };

  // @IPC(Method)
  virtual int Init(Conf conf = {}) = 0;

  // @IPC(Method)
  virtual Conf conf() const = 0;
};

}  // namespace ns2
}  // namespace ns1
