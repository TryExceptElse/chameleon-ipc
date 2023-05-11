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
/**
 * @brief Header declaring built-in serialization functions.
 *
 * There are three serialization function varieties used by CIPC:
 * serialized_size(), serialize(), and deserialize(). These functions
 * respectively return the serialized size of an object in memory,
 * serialize the object, or deserialize to an object of a given type.
 * If serialization or deserialization cannot be completed due to
 * insufficient buffer size, a 0 is returned.
 */
#ifndef CIPC_SERIALIZE_H_
#define CIPC_SERIALIZE_H_

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <deque>
#include <list>
#include <map>
#include <string>
#include <type_traits>
#include <unordered_map>
#include <vector>

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

template<typename T>
using enable_if_integral_serializable = typename std::enable_if<
    std::is_same<T, std::uint8_t>::value ||
        std::is_same<T, std::uint16_t>::value ||
        std::is_same<T, std::uint32_t>::value ||
        std::is_same<T, std::uint64_t>::value ||
        std::is_same<T, std::int8_t>::value ||
        std::is_same<T, std::int16_t>::value ||
        std::is_same<T, std::int32_t>::value ||
        std::is_same<T, std::int64_t>::value,
    bool>;

// Number types

template<
    typename T,
    typename enable_if_integral_serializable<T>::type = true>
std::size_t serialize(const T& x, void* buf, std::size_t buf_size) {
  if (buf_size < sizeof(T)) {
    return 0;
  }
  const typename std::make_unsigned<T>::type le = host_to_le(x);
  std::memcpy(buf, &le, sizeof(le));
  return sizeof(T);
}

template<
    typename T,
    typename enable_if_integral_serializable<T>::type = true>
std::size_t serialized_size(const T& x) {
  return sizeof(T);
}

template<
    typename T,
    typename enable_if_integral_serializable<T>::type = true>
std::size_t deserialize(T* x, const void* buf, std::size_t buf_size) {
  if (buf_size < sizeof(T)) {
    return 0;
  }
  typename std::make_unsigned<T>::type le;
  std::memcpy(&le, buf, sizeof(le));
  *x = le_to_host<T>(le);
  return sizeof(T);
}

// Boolean

template<
    typename T,
    typename std::enable_if<std::is_same<T, bool>::value, bool>::type = true>
std::size_t serialize(const T& x, void* buf, std::size_t buf_size) {
  return serialize(static_cast<std::uint8_t>(x), buf, buf_size);
}

template<
    typename T,
    typename std::enable_if<std::is_same<T, bool>::value, bool>::type = true>
std::size_t serialized_size(const T& x) {
  return serialized_size(static_cast<std::uint8_t>(x));
}

template<
    typename T,
    typename std::enable_if<std::is_same<T, bool>::value, bool>::type = true>
std::size_t deserialize(T* x, const void* buf, std::size_t buf_size) {
  std::uint8_t byte;
  const auto n_read_bytes = deserialize(&byte, buf, buf_size);
  *x = static_cast<bool>(byte);
  return n_read_bytes;
}

// Floating point.

template<typename T>
using enable_if_float_serializable = typename std::enable_if<
    std::is_floating_point<T>::value, bool>;

template<
    typename T,
    typename enable_if_float_serializable<T>::type = true>
std::size_t serialize(const T& x, void* buf, std::size_t buf_size) {
  if (buf_size < sizeof(T)) {
    return 0;
  }
  std::memcpy(buf, &x, sizeof(x));
  return sizeof(x);
}

template<
    typename T,
    typename enable_if_float_serializable<T>::type = true>
std::size_t serialized_size(const T& x) {
  return sizeof(x);
}
 
template<
    typename T,
    typename enable_if_float_serializable<T>::type = true>
std::size_t deserialize(T* x, const void* buf, std::size_t buf_size) {
  if (buf_size < sizeof(T)) {
    return 0;
  }
  std::memcpy(x, buf, sizeof(T));
  return sizeof(T);
}

// Builtin complex types

std::size_t serialize(const std::string& x, void* buf, std::size_t buf_size);

std::size_t serialized_size(const std::string& x);

std::size_t deserialize(std::string* x, const void* buf, std::size_t buf_size);

// List-like types

using CollectionSize = std::uint32_t;

template<template<typename...> class T, template<typename...> class U>
struct is_same_template : std::false_type {};

template<template<typename...> class T>
struct is_same_template<T, T> : std::true_type {};

template<template<typename...> class T>
using enable_if_list_like = typename std::enable_if<
    is_same_template<T, std::deque>::value ||
        is_same_template<T, std::list>::value ||
        is_same_template<T, std::vector>::value,
    bool>;

template<
    template<typename...> class Collection,
    typename Item,
    typename enable_if_list_like<Collection>::type = true>
std::size_t serialized_size(const Collection<Item>& x) {
  std::size_t size = sizeof(CollectionSize);
  for (const auto& item : x) {
    size += serialized_size(item);
  }
  return size;
}

template<
    template<typename...> class Collection,
    typename Item,
    typename enable_if_list_like<Collection>::type = true>
std::size_t serialize(
    const Collection<Item>& x, void* buf, std::size_t buf_size) {
  const auto size = serialized_size(x);
  auto* cursor = reinterpret_cast<uint8_t*>(buf);
  const auto* start = cursor;
  if (size > buf_size) {
    return 0;
  }
  const CollectionSize len = x.size();
  const auto len_size = serialize(len, buf, buf_size);
  if (len_size == 0) {
    return 0;
  }
  buf_size -= len_size;
  cursor += len_size;
  for (const auto& item : x) {
    const auto written_bytes = serialize(item, cursor, buf_size);
    if (written_bytes == 0) {
      return 0;
    }
    buf_size -= written_bytes;
    cursor += written_bytes;
  }
  return cursor - start;
}

template<
    template<typename...> class Collection,
    typename Item,
    typename enable_if_list_like<Collection>::type = true>
std::size_t deserialize(
    Collection<Item>* x, const void* buf, std::size_t buf_size) {
  x->clear();
  auto* cursor = reinterpret_cast<const uint8_t*>(buf);
  const auto* start = cursor;
  CollectionSize n_items;
  auto n_read_bytes = deserialize(&n_items, cursor, buf_size);
  if (n_read_bytes == 0) {
    return 0;
  }
  cursor += n_read_bytes;
  buf_size -= n_read_bytes;
  while (n_items > 0) {
    Item item;
    n_read_bytes = deserialize(&item, cursor, buf_size);
    if (n_read_bytes == 0) {
      return 0;
    }
    x->push_back(std::move(item));
    cursor += n_read_bytes;
    buf_size -= n_read_bytes;
    --n_items;
  }
  return cursor - start;
}

// Map-like types

template<template<typename...> class T>
using enable_if_map_like = typename std::enable_if<
    is_same_template<T, std::map>::value ||
        is_same_template<T, std::multimap>::value ||
        is_same_template<T, std::unordered_map>::value ||
        is_same_template<T, std::unordered_multimap>::value,
    bool>;

template<
    template<typename...> class Map,
    typename Key,
    typename Value,
    typename enable_if_map_like<Map>::type = true>
std::size_t serialized_size(const Map<Key, Value>& x) {
  std::size_t size = sizeof(CollectionSize);
  for (const auto& pair : x) {
    size += serialized_size(pair.first);
    size += serialized_size(pair.second);
  }
  return size;
}

template<
    template<typename...> class Map,
    typename Key,
    typename Value,
    typename enable_if_map_like<Map>::type = true>
std::size_t serialize(
    const Map<Key, Value>& x, void* buf, std::size_t buf_size) {
  const auto size = serialized_size(x);
  auto* cursor = reinterpret_cast<uint8_t*>(buf);
  const auto* start = cursor;
  if (size > buf_size) {
    return 0;
  }
  const CollectionSize len = x.size();
  const auto len_size = serialize(len, buf, buf_size);
  if (len_size == 0) {
    return 0;
  }
  buf_size -= len_size;
  cursor += len_size;
  for (const auto& pair : x) {
    {
      const auto written_bytes = serialize(pair.first, cursor, buf_size);
      if (written_bytes == 0) {
        return 0;
      }
      buf_size -= written_bytes;
      cursor += written_bytes;
    }
    {
      const auto written_bytes = serialize(pair.second, cursor, buf_size);
      if (written_bytes == 0) {
        return 0;
      }
      buf_size -= written_bytes;
      cursor += written_bytes;
    }
  }
  return cursor - start;
}

template<
    template<typename...> class Map,
    typename Key,
    typename Value,
    typename enable_if_map_like<Map>::type = true>
std::size_t deserialize(
    Map<Key, Value>* x, const void* buf, std::size_t buf_size) {
  x->clear();
  auto* cursor = reinterpret_cast<const uint8_t*>(buf);
  const auto* start = cursor;
  CollectionSize n_items;
  auto n_read_bytes = deserialize(&n_items, cursor, buf_size);
  if (n_read_bytes == 0) {
    return 0;
  }
  cursor += n_read_bytes;
  buf_size -= n_read_bytes;
  while (n_items > 0) {
    Key key;
    n_read_bytes = deserialize(&key, cursor, buf_size);
    if (n_read_bytes == 0) {
      return 0;
    }
    cursor += n_read_bytes;
    buf_size -= n_read_bytes;
    Value value;
    n_read_bytes = deserialize(&value, cursor, buf_size);
    if (n_read_bytes == 0) {
      return 0;
    }
    cursor += n_read_bytes;
    buf_size -= n_read_bytes;
    --n_items;
    x->insert(std::make_pair(std::move(key), std::move(value)));
  }
  return cursor - start;
}

// Option

}  // namespace cipc

#endif  // CIPC_SERIALIZE_H_
