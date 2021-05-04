
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

#define PGH_ASSERT(expr, msg) if (!(expr)) throw std::exception{(msg)}

#define FOR_EACH_INT_TYPE(F) \
F(bool, "bool")\
F(float, "float")\
F(double, "double")\
F(int8_t, "i8")\
F(int16_t, "i16")\
F(int32_t, "i32")\
F(int64_t, "i64")\
F(uint8_t, "u8")\
F(uint16_t, "u16")\
F(uint32_t, "u32")\
F(uint64_t, "u64")

}
