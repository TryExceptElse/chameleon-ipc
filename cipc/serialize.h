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
#ifndef CIPC_SERIALIZE_H_
#define CIPC_SERIALIZE_H_

#include <cstddef>
#include <cstdint>
#include <type_traits>

#include "cipc/platform.h"

#if !defined(CIPC_USE_GNU_BUILTINS)
#  if defined(__GNUC__)
#    define CIPC_USE_GNU_BUILTINS 1
#  else
#    define CIPC_USE_GNU_BUILTINS 0
#  endif
#endif

#if !defined(CIPC_USE_LITTLE_ENDIAN_IMPL)
#  if defined(CIPC_LITTLE_ENDIAN)
#    define CIPC_USE_LITTLE_ENDIAN_IMPL 1
#  else
#    define CIPC_USE_LITTLE_ENDIAN_IMPL 0
#  endif
#endif

#if !defined(CIPC_USE_BIG_ENDIAN_IMPL)
#  if defined(CIPC_BIG_ENDIAN)
#    define CIPC_USE_BIG_ENDIAN_IMPL 1
#  else
#    define CIPC_USE_BIG_ENDIAN_IMPL 0
#  endif
#endif

namespace cipc {

template<typename T>
std::size_t serialize(const T& x, void* buf, std::size_t buf_size);

template<typename T>
std::size_t deserialize(T* x, const void* buf, std::size_t buf_size);

// Serialization util.

template<typename T>
T byte_swap(T x);

template<>
inline std::uint8_t byte_swap<std::uint8_t>(std::uint8_t x) {
  return x;
}

#if CIPC_USE_GNU_BUILTINS == 1  // Also handles clang.

template<>
inline std::uint16_t byte_swap<std::uint16_t>(std::uint16_t x) {
  return __builtin_bswap16(x);
}

template<>
inline std::uint32_t byte_swap<std::uint32_t>(std::uint32_t x) {
  return __builtin_bswap32(x);
}

template<>
inline std::uint64_t byte_swap<std::uint64_t>(std::uint64_t x) {
  return __builtin_bswap64(x);
}

#else

template<>
std::uint16_t byte_swap<std::uint16_t>(std::uint16_t x) {
  return (x >> 8) | (x << 8);
}

template<>
std::uint32_t byte_swap<std::uint32_t>(std::uint32_t x) {
  return byte_swap<std::uint16_t>(x) << 16 | byte_swap<std::uint16_t>(x >> 16);
}

template<>
std::uint64_t byte_swap<std::uint64_t>(std::uint64_t x) {
  return byte_swap<std::uint32_t>(x) << 32 | byte_swap<std::uint32_t>(x >> 32);
}

#endif

template<typename T>
typename std::make_unsigned<T>::type host_to_le(T x) {
#if CIPC_USE_LITTLE_ENDIAN_IMPL == 1
  return static_cast<typename std::make_unsigned<T>::type>(x);
#elif CIPC_USE_BIG_ENDIAN_IMPL == 1 && CIPC_USE_GNU_BUILTINS == 1
  return byte_swap(static_cast<typename std::make_unsigned<T>::type>(x));
#else
  std::uint8_t bytes[sizeof(T)];
  for (std::size_t i = 0; i < sizeof(T); ++i) {
    bytes[i] = x & 0xFF;
    x >>= 8;
  }
  return *reinterpret_cast<typename std::make_unsigned<T>::type*>(bytes);
#endif
}

template<typename T>
T le_to_host(typename std::make_unsigned<T>::type x) {
#if CIPC_USE_LITTLE_ENDIAN_IMPL == 1
  return static_cast<T>(x);
#elif CIPC_USE_BIG_ENDIAN_IMPL == 1 && CIPC_USE_GNU_BUILTINS == 1
  return static_cast<T>(byte_swap(x));
#else
  const auto* bytes = reinterpret_cast<std::uint8_t*>(&x);
  T result = 0;
  for (std::size_t i = 0; i < sizeof(T); ++i) {
    result <<= 8;
    result |= bytes[sizeof(T) - 1 - i];
  }
  return result;
#endif
}

// Specializations.

#define CIPC_SERIALIZATION_SPECIALIZATION(TYPE) \
  template<> \
  std::size_t serialize<TYPE>(const TYPE& x, void* buf, std::size_t buf_size); \
  \
  template<> \
  std::size_t deserialize<TYPE>(TYPE* x, const void* buf, std::size_t buf_size);
  
// Number types

CIPC_SERIALIZATION_SPECIALIZATION(uint8_t)
CIPC_SERIALIZATION_SPECIALIZATION(uint16_t)
CIPC_SERIALIZATION_SPECIALIZATION(uint32_t)
CIPC_SERIALIZATION_SPECIALIZATION(uint64_t)
CIPC_SERIALIZATION_SPECIALIZATION(int8_t)
CIPC_SERIALIZATION_SPECIALIZATION(int16_t)
CIPC_SERIALIZATION_SPECIALIZATION(int32_t)
CIPC_SERIALIZATION_SPECIALIZATION(int64_t)

}  // namespace cipc

#endif  // CIPC_SERIALIZE_H_
