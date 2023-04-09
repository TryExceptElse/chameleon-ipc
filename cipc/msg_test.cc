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
#include <vector>

#include "gtest/gtest.h"

#include "cipc/msg.h"

namespace cipc {

TEST(CipcMsg, SimpleRequestCreation) {
  const auto call_id = 0xABCD;
  const std::uint32_t arg1 = 0xDEADBEEF;
  const std::uint16_t arg2 = 0xBEEF;
  const std::uint64_t arg3 = 0xA1B1'C1D1'A2B2'C2D2;
  const Msg::MethodId method_id = 0x11223344;
  const Msg::ObjectId object_id = 0x1122334455667788;
  auto msg = Msg::BuildRequest(
      call_id, method_id, object_id, arg1, arg2, arg3);
  EXPECT_EQ(msg.preamble(), Msg::kPreamble);
  EXPECT_EQ(msg.type(), Msg::Type::Request);
  EXPECT_EQ(msg.call_id(), call_id);
  const std::vector msg_data(msg.data(), msg.data() + msg.size());
  using u8 = std::uint8_t;
  const std::vector<std::uint8_t> expected{
      u8{Msg::kPreamble}, u8(Msg::Type::Request), 0xCD, 0xAB,  // Header
      0x44, 0x33, 0x22, 0x11,  // Method ID
      0x88, 0x77, 0x66, 0x55,  // Object ID (least significant bits)
      0x44, 0x33, 0x22, 0x11,  // Object ID (most significant bits)
      0xEF, 0xBE, 0xAD, 0xDE,  // Arg1
      0xEF, 0xBE, 0xD2, 0xC2,  // Arg2 + Arg 3 least significant 2 bytes.
      0xB2, 0xA2, 0xD1, 0xC1,  // Arg3 middle 4 bytes.
      0xB1, 0xA1};  // Arg3 most significant bytes.
  EXPECT_EQ(msg_data, expected);
};

TEST(CipcMsg, SimpleResponseCreation) {
  const auto call_id = 0xABCD;
  const std::uint32_t rv = 0xDEADBEEF;
  auto msg = Msg::BuildResponse(call_id, rv);
  EXPECT_EQ(msg.preamble(), Msg::kPreamble);
  EXPECT_EQ(msg.type(), Msg::Type::Response);
  EXPECT_EQ(msg.call_id(), call_id);
  const std::vector msg_data(msg.data(), msg.data() + msg.size());
  using u8 = std::uint8_t;
  const std::vector<std::uint8_t> expected{
      u8{Msg::kPreamble}, u8(Msg::Type::Response), 0xCD, 0xAB,  // Header
      0xEF, 0xBE, 0xAD, 0xDE};  // Rv
  EXPECT_EQ(msg_data, expected);
}

}  // namespace cipc
