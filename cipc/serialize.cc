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


#include "cipc/serialize.h"

#include <cstring>
#include <limits>
#include <list>
#include <vector>

namespace cipc {

// --------------------------------------------------------------------
// std::string serialization.

using StringSize = std::uint32_t;

std::size_t serialize(const std::string& x, void* buf, std::size_t buf_size) {
  const auto size = serialized_size(x);
  if (size > buf_size) {
    return 0;
  }
  const StringSize len = x.size();
  const auto len_size = serialize(len, buf, buf_size);
  buf_size -= len_size;
  std::memcpy(reinterpret_cast<char*>(buf) + len_size, x.data(), x.size());
  return size;
}

std::size_t serialized_size(const std::string& x) {
  return sizeof(StringSize) + x.size();
}

std::size_t deserialize(std::string* x, const void* buf, std::size_t buf_size) {
  StringSize len;
  const auto len_size = deserialize(&len, buf, buf_size);
  buf_size -= len_size;
  const char* start = reinterpret_cast<const char*>(buf) + len_size;
  *x = std::string(start, start + len);
  return len_size + x->size();
}

}  // namespace cipc
