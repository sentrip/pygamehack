import pygamehack as gh

class IntTypes(gh.Struct):
    num_i8 : gh.i8  =  0
    num_i16: gh.i16 =  2
    num_i32: gh.i32 =  4
    num_i64: gh.i64 =  8
    num_u8 : gh.u8  = 16
    num_u16: gh.u16 = 18
    num_u32: gh.u32 = 20
    num_u64: gh.u64 = 24

class TestProgram(gh.Struct):
    marker: gh.uint         = 0x0
    flag  : gh.uint         = 0x8
    update: gh.uint         = 0xC
    n     : IntTypes        = 0x10
