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

namespace cipc {

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

}  // namespace cipc
