
#include <cstdint>
#include <string>

namespace pygamehack {

using u8 = uint8_t;
using u16 = uint16_t;
using u32 = uint32_t;
using u64 = uint64_t;
using i8 = int8_t;
using i16 = int16_t;
using i32 = int32_t;
using i64 = int64_t;
using usize = size_t;
using uptr = uintptr_t;
using string = std::string;


class Address;
class Buffer;
class Hack;
class Process;

template<typename T>
class Variable;

#define PGH_ASSERT(expr, msg) if (!(expr)) throw std::exception{msg}

}
