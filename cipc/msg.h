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

#include <cipc/serialize.h>

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

  static const Preamble kPreamble;

  /**
   * @brief Create new empty message.
   */
  Msg() = default;

  /**
   * @brief Create message with passed data.
   * @param data Data buffer start.
   * @param size Size of data buffer.
   */
  Msg(const void* data, std::size_t size);

  /**
   * @brief Builds request message with passed arguments.
   * @tparam Args Types of arguments to serialize into message.
   * @param call Call ID
   * @param method Method ID
   * @param obj Object ID
   * @param args Arguments to pass with message.
   * @return Request Msg.
   */
  template<typename... Args>
  static auto BuildRequest(
      CallId call, MethodId method, ObjectId obj, const Args&... args) -> Msg;

  /**
   * @brief Builds response message with passed return value.
   * @tparam Rv Return value type to be serialized into message.
   * @param call Call ID being responded to.
   * @param rv Return value.
   * @return Response Msg.
   */
  template<typename Rv>
  static auto BuildResponse(CallId call, const Rv& rv) -> Msg;

  /**
   * @brief Gets preamble code.
   *
   * This value should always be equal to Msg::kPreamble in
   * valid messages.
   *
   * @return Preamble value.
   */
  auto preamble() const -> Preamble;

  /**
   * @brief Gets message type code.
   * @return Type code.
   */
  auto type() const -> Type;

  /**
   * @brief Gets call ID stored in message.
   * @return Call ID.
   */
  auto call_id() const -> CallId;

  /**
   * @brief Gets method ID stored in message.
   *
   * @warning This method is valid to call only on request messages.
   *
   * @return method ID.
   */
  auto method_id() const -> MethodId;

  /**
   * @brief Gets object ID stored in message.
   *
   * @warning This method is valid to call only on request messages.
   *
   * @return Object ID.
   */
  auto object_id() const -> ObjectId;

  /**
   * @brief Gets argument data buffer description.
   *
   * @warning This method is valid to call only on request messages.
   *
   * @return Argument buffer info.
   */
  auto args_data() const -> ArgData;

  /**
   * @brief Gets return value data buffer description.
   *
   * @warning This method is valid to call only on response messages.
   *
   * @return Return value buffer info.
   */
  auto return_value() const -> ArgData;

  /**
   * @brief Gets message data pointer.
   * @return Data buffer start.
   */
  auto data() const -> const uint8_t* { return data_.data(); }

  /**
   * @brief Gets size of message data buffer.
   * @return Data buffer size.
   */
  auto size() const -> std::size_t { return data_.size(); }

 private:
  std::vector<uint8_t> data_;

  static const std::size_t kArgsOffset;
  static const std::size_t kRvOffset;

  static auto PrepareRequestPrefix(
      CallId call, MethodId method, ObjectId obj, std::size_t args_size) -> Msg;

  static auto PrepareResponsePrefix(CallId call, std::size_t rv_size) -> Msg;

  void Write(std::size_t offset, const void* data, std::size_t size);

  template<typename T>
  void Write(std::size_t offset, const T& value);

  template<typename T>
  auto Read(std::size_t offset) const -> T;
};

// Template function implementations

namespace msg_internal {

template<typename T>
std::size_t serialized_size_of_all(T first) {
  return serialized_size(first);
}

template<typename T, typename... Args>
std::size_t serialized_size_of_all(T first, Args... args) {
  return serialized_size(first) + serialized_size_of_all(args...);
}

template<typename T>
std::size_t SerializeToVec(
    std::uint8_t* buf, std::size_t buf_size, T first) {
  return serialize(first, buf, buf_size);
}

template<typename T, typename... Args>
std::size_t SerializeToVec(
    std::uint8_t* buf, std::size_t buf_size, T first, Args... args) {
  const auto n_bytes_written = SerializeToVec(buf, buf_size, first);
  return n_bytes_written + SerializeToVec(
      buf + n_bytes_written, buf_size - n_bytes_written, args...);
}

}  // namespace msg_internal

template<typename... Args>
auto Msg::BuildRequest(
    CallId call, MethodId method, ObjectId obj, const Args&... args) -> Msg {
  const auto args_size = msg_internal::serialized_size_of_all(args...);
  auto msg = PrepareRequestPrefix(call, method, obj, args_size);
  msg_internal::SerializeToVec(
      msg.data_.data() + kArgsOffset, msg.data_.size() - kArgsOffset, args...);
  return msg;
}

template<typename Rv>
auto Msg::BuildResponse(CallId call, const Rv& rv) -> Msg {
  const auto rv_size = serialized_size(rv);
  auto msg = PrepareResponsePrefix(call, rv_size);
  msg_internal::SerializeToVec(
      msg.data_.data() + kRvOffset, msg.data_.size() - kRvOffset, rv);
  return msg;
}

}  // namespace cipc

#endif  // CIPC_MSG_H_
