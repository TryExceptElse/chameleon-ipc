/*
 * Copyright 2023 TryExceptElse
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject
 * to the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 * CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 * TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */
/** @file
 * File documentation.
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
