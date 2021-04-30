
#include <array>
#include <cstdint>
#include <fstream>
#include <filesystem>
#include <iostream>
#include <thread>
#include <string>
#include <vector>

#ifndef ARCH_SUFFIX
#define ARCH_SUFFIX "-64"
#endif

struct IntTypes {
    int8_t num_i8{-15};
    int16_t num_i16{-300};
    int32_t num_i32{-2100000000};
    int64_t num_i64{-10000000000};
    uint8_t num_u8{15};
    uint16_t num_u16{300};
    uint32_t num_u32{2100000000};
    uint64_t num_u64{10000000000};
};

struct StringTypes {
    char buffer[32]{"TestString"};
};

struct PtrTypes {
    volatile uint32_t* marker{};
    IntTypes* n{};
};

struct NestedPtr {
    uint32_t value{};
    NestedPtr* parent{};
    explicit NestedPtr(NestedPtr* parent) : parent{parent}, value{parent ? parent->value + 1 : 555777555} {}
};

struct NestedPtrTypes {
    NestedPtr m;
    NestedPtr* lvl1;
    NestedPtr* lvl2;
    NestedPtr* lvl3;
    
    explicit NestedPtrTypes():
        m{nullptr}, lvl1{new NestedPtr{m}}, lvl2{new NestedPtr{lvl1}}, lvl3{new NestedPtr{lvl2}} {}
};


struct Application {
	static volatile uint32_t marker[4];
	static Application main;

    IntTypes n{};

    StringTypes s{};

    PtrTypes ptr{&marker[0], &n};

    uint8_t pad[64 + 128 + 256 + 512 + 1024];

    volatile uint32_t* marker_pointers[8]{marker, marker, marker, marker, marker, marker, marker, marker};

    NestedPtrTypes nested_ptr{};

	Application() {}
	
	~Application() {}

	void run() { 
		std::cout << "Root - Marker                - " << "0x" << std::hex << &Application::marker << "\n";
		std::cout << "Root - App                   - " << "0x" << std::hex << this << "\n";

        std::cout << "IntTypes -  i8               - " << "0x" << std::hex << ((void*)&n.num_i8) << "\n";
        std::cout << "IntTypes - i16               - " << "0x" << std::hex << &n.num_i16 << "\n";
        std::cout << "IntTypes - i32               - " << "0x" << std::hex << &n.num_i32 << "\n";
        std::cout << "IntTypes - i64               - " << "0x" << std::hex << &n.num_i64 << "\n";
        std::cout << "IntTypes -  u8               - " << "0x" << std::hex << ((void*)&n.num_u8) << "\n";
        std::cout << "IntTypes - u16               - " << "0x" << std::hex << &n.num_u16 << "\n";
        std::cout << "IntTypes - u32               - " << "0x" << std::hex << &n.num_u32 << "\n";
        std::cout << "IntTypes - u64               - " << "0x" << std::hex << &n.num_u64 << "\n";

        std::cout << "String                       - " << "0x" << std::hex << &s << "\n";

        std::cout << "PtrTypes - u32               - " << "0x" << std::hex << &ptr.marker << "\n";
        std::cout << "PtrTypes - IntTypes          - " << "0x" << std::hex << &ptr.n << "\n";

        std::cout << "NestedPtrTypes               - " << "0x" << std::hex << &nested_ptr.m << "\n";

        if (!std::filesystem::exists("MarkerAddress" ARCH_SUFFIX ".txt")) {
            std::ofstream output{"MarkerAddress" ARCH_SUFFIX ".txt"};
            std::string address = std::to_string(uint64_t(&Application::marker));
            output.write(address.c_str(), address.size());
        }

		while (true) { 
            std::this_thread::sleep_for(std::chrono::milliseconds(1)); 
            if (marker[2] != 0) {
                marker[2] = 0;
                marker[3] = (marker[3] + 1) % 4;
            }
        } 
	}
};

volatile uint32_t Application::marker[4] {1234567898, 0, 0, 0};
Application Application::main{};


int main(int argv, char** argc)
{
	Application::main.run();
	return 0;
}
