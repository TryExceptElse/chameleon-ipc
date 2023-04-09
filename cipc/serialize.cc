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

namespace cipc {

// --------------------------------------------------------------------
// Integral type serialization.

#define INTEGRAL_TYPE_SERIALIZATION_FUNCTIONS(TYPE) \
    template<> \
    std::size_t serialize<TYPE>( \
        const TYPE& x, void* buf, std::size_t buf_size) { \
      if (buf_size < sizeof(TYPE)) { \
        return 0; \
      } \
      const typename std::make_unsigned<TYPE>::type le = host_to_le(x); \
      memcpy(buf, &le, sizeof(le)); \
      return sizeof(TYPE); \
    } \
    \
    template<> \
    std::size_t deserialize<TYPE>( \
        TYPE* x, const void* buf, std::size_t buf_size) { \
      if (buf_size < sizeof(TYPE)) { \
        return 0; \
      } \
      typename std::make_unsigned<TYPE>::type le; \
      memcpy(&le, buf, sizeof(le)); \
      *x = le_to_host<TYPE>(le); \
      return sizeof(TYPE); \
    }

INTEGRAL_TYPE_SERIALIZATION_FUNCTIONS(std::uint8_t)
INTEGRAL_TYPE_SERIALIZATION_FUNCTIONS(std::uint16_t)
INTEGRAL_TYPE_SERIALIZATION_FUNCTIONS(std::uint32_t)
INTEGRAL_TYPE_SERIALIZATION_FUNCTIONS(std::uint64_t)
INTEGRAL_TYPE_SERIALIZATION_FUNCTIONS(std::int8_t)
INTEGRAL_TYPE_SERIALIZATION_FUNCTIONS(std::int16_t)
INTEGRAL_TYPE_SERIALIZATION_FUNCTIONS(std::int32_t)
INTEGRAL_TYPE_SERIALIZATION_FUNCTIONS(std::int64_t)

// --------------------------------------------------------------------
// Boolean serialization.

static_assert(sizeof(bool) == 1, "Unexpected bool size.");

template<>
std::size_t serialize<bool>(const bool& x, void* buf, std::size_t buf_size) {
  return serialize<std::uint8_t>(x, buf, buf_size);
}

template<>
std::size_t deserialize<bool>(bool* x, const void* buf, std::size_t buf_size) {
  return deserialize<std::uint8_t>(
      reinterpret_cast<std::uint8_t*>(x), buf, buf_size);
}

// --------------------------------------------------------------------
// Floating point type serialization.

static_assert(
    std::numeric_limits<float>::is_iec559,
    "Only IEEE 754 / IEC 559 float types are currently supported.");
static_assert(
    std::numeric_limits<double>::is_iec559,
    "Only IEEE 754 / IEC 559 double float types are currently supported.");

#define FLOATING_POINT_TYPE_SERIALIZATION_FUNCTIONS(TYPE) \
    template<> \
    std::size_t serialize<TYPE>( \
        const TYPE& x, void* buf, std::size_t buf_size) { \
      if (buf_size < sizeof(TYPE)) { \
        return 0; \
      } \
      memcpy(buf, &x, sizeof(x)); \
      return sizeof(x); \
    } \
    \
    template<> \
    std::size_t deserialize<TYPE>( \
        TYPE* x, const void* buf, std::size_t buf_size) { \
      if (buf_size < sizeof(TYPE)) { \
        return 0; \
      } \
      memcpy(x, buf, sizeof(TYPE)); \
      return sizeof(TYPE); \
    }

FLOATING_POINT_TYPE_SERIALIZATION_FUNCTIONS(float)
FLOATING_POINT_TYPE_SERIALIZATION_FUNCTIONS(double)

// --------------------------------------------------------------------
// std::string serialization.

using StringSize = std::uint32_t;

template<>
std::size_t serialize<std::string>(const std::string& x, void* buf, std::size_t buf_size) {
  const auto size = serialized_size(x);
  if (size > buf_size) {
    return 0;
  }
  const StringSize len = x.length();
  const auto len_size = serialize(len, buf, buf_size);
  buf_size -= len_size;
  memcpy(reinterpret_cast<char*>(buf) + len_size, x.data(), x.size());
  return size;
}

template<>
std::size_t serialized_size<std::string>(const std::string& x) {
  return sizeof(StringSize) + x.size();
}

template<>
std::size_t deserialize<std::string>(std::string* x, const void* buf, std::size_t buf_size) {
  StringSize len;
  const auto len_size = deserialize<StringSize>(&len, buf, buf_size);
  buf_size -= len_size;
  const char* start = reinterpret_cast<const char*>(buf) + len_size;
  *x = std::string(start, start + len);
  return len_size + x->size();
}

// --------------------------------------------------------------------

}  // namespace cipc
