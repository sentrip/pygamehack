
#include <cstdint>
#include <iostream>
#include <type_traits>
#include <string>
#include <thread>
#include <fstream>


#define PP_STR(x) #x
#define STR_8       "TestStr"
#define PTR_BEEF    ((void*)0xdeadbeefll)
#define VALUE       0b10100101
#define VALUEF      4.0


#define PRINT_OFFSET(name, T) std::cout << "\t" PP_STR(name) " - \t" << std::hex << "0x" << offsetof(T, name) << "\n";
#define PRINT_ADDRESS(name) std::cout << "\t" PP_STR(name) " - \t" << std::hex << "0x" << ((void*)&this->name) << "\n";


struct Empty {};


//region Basic

#define BASIC_FOR_EACH_PROP(F) F(i8); F(i16); F(i32); F(i64); F(u8); F(u16); F(u32); F(u64); F(b); F(f); F(d); F(str); F(arr); F(sz); F(ptr);

template<size_t N> struct SZ {};
template<> struct SZ<4> { size_t sz{VALUE}; uint8_t p[4]{}; };
template<> struct SZ<8> { size_t sz{VALUE}; };

template<size_t N> struct PV {};
template<> struct PV<4> { void* ptr{PTR_BEEF}; uint8_t p[4]{}; };
template<> struct PV<8> { void* ptr{PTR_BEEF}; };


struct BasicTypes {
    int8_t                  i8{3};              //  0x0 - 0
    uint8_t     _0[7]{};
    int16_t                 i16{VALUE};         //  0x8 - 8
    uint8_t     _1[6]{};
    int32_t                 i32{VALUE};         // 0x10 - 16
    uint8_t     _2[4]{};
    int64_t                 i64{VALUE};         // 0x18 - 24
    uint8_t                 u8{VALUE};          // 0x20 - 32
    uint8_t     _3[7]{};
    uint16_t                u16{VALUE};         // 0x28 - 40
    uint8_t     _4[6]{};
    uint32_t                u32{VALUE};         // 0x30 - 48
    uint8_t     _5[4]{};
    uint64_t                u64{VALUE};         // 0x38 - 56
    bool                    b{true};            // 0x40 - 64
    uint8_t     _6[7]{};
    float                   f{VALUEF};          // 0x48 - 72
    uint8_t     _7[4]{};
    double                  d{VALUEF};          // 0x50 - 80
    char                    str[8]{STR_8};      // 0x58 - 88
    uint32_t                arr[4]{4,3,2,1};    // 0x60 - 96
    SZ<sizeof(void*)>       sz{};               // 0x70 - 112
    PV<sizeof(void*)>       ptr{};              // 0x78 - 120

    static void print_offsets()
    {
        std::cout << "BasicTypes\n";
        #define F(name) PRINT_OFFSET(name, BasicTypes)
        BASIC_FOR_EACH_PROP(F)
        #undef F
        std::cout << "\n";
    }

    void print_addresses()
    {
        std::cout << "BasicTypes\n";
        BASIC_FOR_EACH_PROP(PRINT_ADDRESS)
        std::cout << "\n";
    }
};

static_assert(sizeof(BasicTypes) == 128);

//endregion

//region Pointer

//endregion

//region Driver

struct Driver {
    volatile uint64_t dinc{};
    volatile uint64_t cnt{};

    void update()
    {
        if (dinc) {
            cnt = (cnt + 1) % 4;
            dinc = 0;
        }
    }

    static void print_offsets()
    {
        std::cout << "Driver\n";
        PRINT_OFFSET(dinc, Driver)
        PRINT_OFFSET(cnt, Driver)
        std::cout << "\n";
    }

    void print_addresses()
    {
        std::cout << "Driver\n";
        PRINT_ADDRESS(dinc)
        PRINT_ADDRESS(cnt)
        std::cout << "\n";
    }
};

//endregion

//region Program

struct Program {
    BasicTypes basic{};                         //  0x0 - 0
    Driver driver{};                            // 0x80 - 128

    void update()
    {
        driver.update();
    }

    static void print_offsets()
    {
        std::cout << "Program\n";
        PRINT_OFFSET(basic, Program)
        PRINT_OFFSET(driver, Program)
        std::cout << "\n";
        BasicTypes::print_offsets();
        Driver::print_offsets();
    }

    void print_addresses()
    {
        std::cout << "Program\n";
        PRINT_ADDRESS(basic)
        PRINT_ADDRESS(driver)
        std::cout << "\n";
        basic.print_addresses();
        driver.print_addresses();
    }
};

//endregion


int main()
{
    static Program static_program{};
    Program stack_program{};
    Program* heap_program{new Program{}};
    Program* programs[3]{&static_program, &stack_program, heap_program};

    std::ofstream output{"MarkerAddress" ARCH_SUFFIX ".txt"};
    for (auto* program: programs) {
        if (program != programs[0]) { output.write(",", 1); }
        std::string address = std::to_string(uint64_t(program));
        output.write(address.c_str(), address.size());
    }
    output.close();

    for (uint32_t i = 0; i < 100; ++i) std::cout << "#";
    std::cout << "\n";
    std::cout << "Offsets\n\n";
    Program::print_offsets();
    for (uint32_t i = 0; i < 100; ++i) std::cout << "#";
    std::cout << "\n";
    const char* address_type[3]{"Static", "Stack", "Heap"};
    int i = 0;
    for (auto* program: programs) {
        std::cout << "Addresses - " << address_type[i++] << "\n\n";
        program->print_addresses();
        for (uint32_t i = 0; i < 100; ++i) std::cout << "#";
        std::cout << "\n";
    }

    for (;;) {
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
        static_program.update();
        stack_program.update();
        heap_program->update();
    }

    return 0;
}