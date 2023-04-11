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

#include <limits>
#include <vector>

#include "gtest/gtest.h"

#include "cipc/serialize.h"

namespace cipc {

namespace {

using namespace std::string_literals;  // NOLINT

class CipcSerializeTest : public ::testing::Test {
 protected:
  std::vector<uint8_t> buf_ = std::vector<uint8_t>(128);
};

#define ROUND_TRIP_TEST(NAME_SUFFIX, X) \
    TEST_F(CipcSerializeTest, RoundTrip##NAME_SUFFIX) { \
      const auto x = X; \
      using Type = std::remove_const_t<decltype(x)>; \
      const auto size = serialized_size(x); \
      EXPECT_EQ(serialize<Type>(x, buf_.data(), buf_.size()), size) \
          << "serialize() returned unexpected size."; \
      Type result{}; \
      EXPECT_EQ(deserialize<Type>(&result, buf_.data(), buf_.size()), size) \
          << "deserialize() returned unexpected size."; \
      EXPECT_EQ(result, x) << "Final value was other than expected."; \
    }

#define SIZE_TEST(NAME_SUFFIX, TYPE, X, EXPECTED) \
    TEST_F(CipcSerializeTest, TYPE##Size##NAME_SUFFIX) { \
      const TYPE x = X; \
      EXPECT_EQ(serialized_size(x), EXPECTED); \
    }

#define SIMPLE_SIZE_TEST(NAME_SUFFIX, TYPE, X) \
    SIZE_TEST(NAME_SUFFIX, TYPE, X, sizeof(TYPE));

#define NUMBER_TESTS(TYPE) \
    ROUND_TRIP_TEST(TYPE##0, TYPE{0}) \
    ROUND_TRIP_TEST(TYPE##1, TYPE{1}) \
    ROUND_TRIP_TEST(TYPE##Min, std::numeric_limits<TYPE>::min()) \
    ROUND_TRIP_TEST(TYPE##Max, std::numeric_limits<TYPE>::max()) \
    SIMPLE_SIZE_TEST(0, TYPE, 0) \
    SIMPLE_SIZE_TEST(1, TYPE, 1)

NUMBER_TESTS(uint8_t)
NUMBER_TESTS(uint16_t)
NUMBER_TESTS(uint32_t)
NUMBER_TESTS(uint64_t)
NUMBER_TESTS(int8_t)
NUMBER_TESTS(int16_t)
NUMBER_TESTS(int32_t)
NUMBER_TESTS(int64_t)
ROUND_TRIP_TEST(True, true)
ROUND_TRIP_TEST(False, false)
SIZE_TEST(True, bool, true, 1)
SIZE_TEST(False, bool, false, 1)
NUMBER_TESTS(float)
NUMBER_TESTS(double)
ROUND_TRIP_TEST(ShortString, "Short"s)
ROUND_TRIP_TEST(LongString, "ARatherLongStringThatExceedsSmallBufLen"s)
ROUND_TRIP_TEST(EmptyString, ""s)

}  // namespace

}  // namespace cipc
