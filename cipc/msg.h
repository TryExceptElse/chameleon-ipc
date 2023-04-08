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
#ifndef CIPC_MSG_H_
#define CIPC_MSG_H_

#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace cipc {

/**
 * @brief The message type stores a CIPC message, complete with
 * formatting.
 *
 * @note this Type is intended for internal use, and is not likely to
 * be useful to end users.
 *
 * The following fields are present, although they may have different
 * meaning or be disallowed in response messages:
 *
 * Request:
 * * HEADER: 32b (4B): Contains the following bitfields:
 *   * Preamble: 8b : 0xC: Helps detect malformed messages, in combination
 *     with the following 'Message type' field.
 *   * Message type: 8b. Should be checked before any following fields.
 *     * 1 for 'call' messages.
 *   * Call ID: 16b (2B): Identifier for this method call. Allows return
 *     value to be paired with original method call.
 * * METHOD_ID: 32b (4B): Method ID
 * * OBJECT_ID: 64b (8B) Identifier of object being called.
 *   * 0 (null) Indicates that the service object is being called.
 * * Args: Size and types determined from method ID.
 */
class Msg {
 public:
  enum class Type { Request = 1, Response = 2 };
  using CallId = std::uint16_t;
  using MethodId = std::uint32_t;
  using ObjectId = std::uint64_t;
  using Preamble = std::uint8_t;
  using ArgData = struct { const void* data; std::size_t size; };

  Msg() = default;
  Msg(const void* data, std::size_t size);

  static auto BuildRequest(
      CallId call_id, MethodId method, ObjectId obj, ArgData args) -> Msg;

  static auto BuildResponse(CallId call_id, ArgData rv) -> Msg;

  auto preamble() const -> Preamble;
  auto type() const -> Type;
  auto call_id() const -> CallId;
  auto method_id() const -> MethodId;
  auto object_id() const -> ObjectId;
  auto args_data() const -> ArgData;
  auto return_value() const -> ArgData;

 private:
  std::vector<uint8_t> data_;

  void Write(std::size_t offset, const void* data, std::size_t size);

  template<typename T>
  void Write(std::size_t offset, const T& value);

  template<typename T>
  auto Read(std::size_t offset) const -> T;
};

}  // namespace cipc

#endif  // CIPC_MSG_H_
