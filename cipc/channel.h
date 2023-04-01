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
#ifndef CIPC_CHANNEL_H_
#define CIPC_CHANNEL_H_

#include <memory>
#include <string>

namespace cipc {

// Forward declarations.
class Msg;
class Response;

class Channel {
 public:
  static std::unique_ptr<Channel> Connect(std::string path);
  static std::unique_ptr<Channel> Bind(std::string path);

  virtual void Accept(std::function<void(const Msg&, Response*)>);
  virtual void Send(void* data, std::size_t size);
  void Send(const Msg& msg);
};

}  // namespace cipc

#endif  // CIPC_CHANNEL_H_
