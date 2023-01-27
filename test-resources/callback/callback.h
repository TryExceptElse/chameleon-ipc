#include <functional>
#include <string>

// @IPC(Callback)
using Callback = std::function<void(int, std::string)>;
