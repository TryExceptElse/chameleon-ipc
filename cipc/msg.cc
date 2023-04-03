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

void MsgBuilder::EnsureArgSpace(std::size_t space) {
  if (args_space() >= space) {
    return;
  }
  assert(args_capacity_ > 0);
  std::size_t new_capacity = args_capacity_;
  do {
    new_capacity *= 2;
  } while (new_capacity - args_size_ < space);
  auto new_buf = std::unique_ptr<std::uint8_t[]>(new uint8_t[new_capacity]);
  memcpy(new_buf.get(), arg_buffer_.get(), args_size_);
  arg_buffer_ = std::move(new_buf);
  args_capacity_ = new_capacity;
}

}  // namespace cipc
