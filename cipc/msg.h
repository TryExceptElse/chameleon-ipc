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
 * * HEADER: 64b (8B): Contains the following bitfields:
 *   * Preamble: 8b : 0xC: Helps detect malformed messages, in
 *     combination with the following 'Message type' field.
 *   * Message type: 8b. Should be checked before any following fields.
 *     1 for 'call' messages.
 *   * Call ID: 16b (2B): Identifier for this method call. Allows return
 *     value to be paired with original method call.
 *   * Extended method ID length: 2b: Indicates whether 0-3 extra 4B
 *     method ID words (4B) are present.
 *   * Method ID: 24b (3B): First 3 method ID bytes.
 *   * OBJECT_ID: 64b (8B) Identifier of object being called.
 *     * 0 (null) Indicates that the service object is being called.
 * * METHOD_ID: 0-128b (0-16B): Unique identifier for method being
 *   invoked. This is unique to the specific overloaded
 *   method implementation.
 * * Args: Variable size. Determined by argument types associated with
 *   the method ID.
 * Number of words is indicated
 */
class Msg {
 public:
  enum class Type { Request = 1, Response = 2 };
  using CallId = std::uint16_t;

  Msg();
  Msg(void* data, std::size_t size);

  Msg& set_type(Type type);

  void* data();
  const void* data() const;
  std::size_t size() const;
};

class MsgBuilder {
 public:
  MsgBuilder& set_type(Msg::Type type);
  MsgBuilder& set_call_id(Msg::CallId id);
  MsgBuilder& set_method_id(const uint8_t* bytes, std::size_t size);
  MsgBuilder& set_object_id(std::uint64_t id);

  template<typename ArgType>
  MsgBuilder& add_arg(const ArgType& arg);

 private:
  Msg::Type type_;
  Msg::CallId call_id_;
  std::uint8_t method_id_len_;
  std::uint32_t method_id_start_;
  std::uint64_t object_id_;
  std::array<std::uint32_t, 4> extended_method_id_;
  std::unique_ptr<std::uint8_t[]> arg_buffer_;
  std::size_t args_size_;
  std::size_t args_capacity_;

  /**
   * @brief Ensure unused argument buffer space is available.
   * @param space Required unused space in bytes.
   */
  void EnsureArgSpace(std::size_t space);

  /**
   * @brief Unused argument buffer space.
   *
   * @return Unused space in bytes.
   */
  std::size_t args_space() const { return args_capacity_ - args_size_; }

  std::uint8_t* args_end() { return &arg_buffer_[args_size_]; }
};

// ---------------------------------------------------------------------
// Template function implementations

template<typename ArgType>
MsgBuilder& MsgBuilder::add_arg(const ArgType& arg) {
  const std::size_t required_space = serialized_size(arg);
  EnsureArgSpace(required_space);
  const std::size_t written_size = serialize(arg, args_end(), args_space());
  assert(written_size < args_space());
  args_size_ += written_size;
}

}  // namespace cipc

#endif  // CIPC_MSG_H_

