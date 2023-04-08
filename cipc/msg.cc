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
#include "cipc/msg.h"

#include <cstring>
#include <utility>

namespace cipc {

namespace {

constexpr auto kHeaderSize =
    sizeof(Msg::Preamble) + sizeof(Msg::Type) + sizeof(Msg::CallId);
constexpr auto kTypeOffset = sizeof(Msg::Preamble);
constexpr auto kCallIdOffset = kTypeOffset + sizeof(Msg::Type);
constexpr auto kMethodIdOffset = kCallIdOffset + sizeof(Msg::CallId);
constexpr auto kObjectIdOffset = kMethodIdOffset + sizeof(Msg::MethodId);
constexpr auto kArgsOffset = kObjectIdOffset + sizeof(Msg::ObjectId);
constexpr auto kRvOffset = kCallIdOffset + sizeof(Msg::CallId);
constexpr auto kPreamble = 'C';

auto as_bytes(const void* data) -> const std::uint8_t* {
  return reinterpret_cast<const std::uint8_t*>(data);
}

}  // namespace

Msg::Msg(const void* data, std::size_t size)
    : data_(as_bytes(data), as_bytes(data) + size) {}

auto Msg::BuildRequest(
    CallId call_id, MethodId method, ObjectId obj, ArgData args) -> Msg {
  Msg msg;
  msg.data_.resize(
      kHeaderSize + sizeof(ObjectId) + sizeof(MethodId) + args.size);
  msg.Write(0, kPreamble);
  msg.Write(kTypeOffset, Msg::Type::Request);
  msg.Write(kCallIdOffset, call_id);
  msg.Write(kMethodIdOffset, method);
  msg.Write(kObjectIdOffset, obj);
  msg.Write(kArgsOffset, args.data, args.size);
  return msg;
}

auto Msg::BuildResponse(CallId call_id, ArgData rv) -> Msg {
  Msg msg;
  msg.data_.resize(kHeaderSize + rv.size);
  msg.Write(0, kPreamble);
  msg.Write(kTypeOffset, Msg::Type::Response);
  msg.Write(kCallIdOffset, call_id);
  msg.Write(kRvOffset, rv.data, rv.size);
  return msg;
}

auto Msg::preamble() const -> Preamble {
  return Read<Preamble>(0);
}

auto Msg::type() const -> Type {
  return Read<Type>(kTypeOffset);
}

auto Msg::call_id() const -> CallId {
  return Read<CallId>(kCallIdOffset);
}

auto Msg::method_id() const -> MethodId {
  assert(type() == Type::Request);
  return Read<MethodId>(kMethodIdOffset);
}

auto Msg::object_id() const -> ObjectId {
  assert(type() == Type::Request);
  return Read<MethodId>(kObjectIdOffset);
}

auto Msg::args_data() const -> ArgData {
  assert(type() == Type::Request);
  return {data_.data() + kArgsOffset, data_.size() - kArgsOffset};
}

auto Msg::return_value() const -> ArgData {
  assert(type() == Type::Response);
  return {data_.data() + kRvOffset, data_.size() - kRvOffset};
}

// Private methods

void Msg::Write(std::size_t offset, const void* data, std::size_t size) {
  assert(offset + size < data_.size());
  std::memcpy(&data_[offset], data, size);
}

template <typename T>
void Msg::Write(std::size_t offset, const T& value) {
  Write(offset, &value, sizeof(T));
}

template <typename T>
auto Msg::Read(std::size_t offset) const -> T {
  assert(offset + sizeof(T) < data_.size());
  T obj;
  std::memcpy(&obj, data_.data() + offset, sizeof(T));
  return obj;
}

}  // namespace cipc
