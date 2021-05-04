#ifndef PYTOSTRING_H
#define PYTOSTRING_H

#include "pywrappers.h"

namespace pygamehack {

//region Python wrappers - ToString

template<typename T>
struct TypeName { const char* operator()() const noexcept { return ""; } };

#define F(T, name) template<> struct TypeName<T> { const char* operator()() const noexcept { return name; } };

F(Buffer, "buf")
//F(PtrToBuffer, "p_buf")
FOR_EACH_INT_TYPE(F)

#undef F


template <typename I>
string number_to_hex_string(I w, usize hex_len = sizeof(I)<<1)
{
    static const char* digits = "0123456789ABCDEF";
    string rc(hex_len,'0');
    for (usize i=0, j=(hex_len-1)*4 ; i<hex_len; ++i,j-=4)
        rc[i] = digits[(w>>j) & 0x0f];
    return rc;
};


static constexpr auto address_make_string = [](u64 value, Process::Arch arch)
{
    if (arch == Process::Arch::X86) {
        return "0x" + number_to_hex_string<u32>(u32(value));
    } else if (arch == Process::Arch::X64) {
        return "0x" + number_to_hex_string<u64>(u64(value));
    }
    else {
        char buf[128]{};
        int size = sprintf(buf, "0x%llX", u64(value));
        return string{buf};
    }
};

static constexpr auto process_tostring = [](Process& v)
{
    string s{"Process(pid="};
    s.append(std::to_string(v.pid()));
    s.append(")");
    return s;
};

static constexpr auto hack_tostring = [](Hack& v)
{
    string s{"Hack("};

    s.append(")");
    return s;
};

static constexpr auto address_tostring = [](Address& v)
{
    string s{"Address(0x"};
    if (v.process().arch() == Process::Arch::X86) {
        s.append(number_to_hex_string<u32>(u32(v.value())));
    }
    else {
        s.append(number_to_hex_string<u64>(u64(v.value())));
    }
    switch(v.type()) {
        case Address::Type::MANUAL: s.append(", Manual");break;
        case Address::Type::STATIC: s.append(", Static"); break;
        case Address::Type::DYNAMIC: s.append(", Dynamic"); break;
    }
    s.append(")");
    return s;
};

static constexpr auto buffer_tostring = [](Buffer& v)
{
    string s{"Buffer(size="};
    s.append(std::to_string(v.size()));
    s.append(")");
    return s;
};

template<typename T>
static constexpr string variable_tostring(Variable<T>& v)
{
    string s{TypeName<T>()()};
    s.append("(0x");
    auto& addr = v.address();
    if (addr.process().arch() == Process::Arch::X86) {
        s.append(number_to_hex_string<u32>(u32(addr.value())));
    }
    else {
        s.append(number_to_hex_string<u64>(u64(addr.value())));
    }
    s.append(")");
    return s;
}

static constexpr auto instruction_tostring = [](Instruction& v)
{
    string s{"Instruction(type="};
    FOR_EACH_INSTRUCTION_TYPE([&](Instruction::Type t, const char* name){ if (t == v.type) { s.append(name); } })
    s.append(")");
    return s;
};

static constexpr auto hack_cheat_engine_settings_tostring = [](Hack::CE::Settings& settings)
{
    string s{"CheatEnginePointerScanSettings(max_level="};
    s.append(std::to_string(settings.max_level));
    s.append(", max_offset=");
    s.append(std::to_string(settings.max_offset));
    s.append(", is_compressed=");
    s.append(settings.is_compressed ? "True" : "False");
    s.append(", is_aligned=");
    s.append(settings.is_aligned ? "True" : "False");
    s.append(", ends_with_offsets=[");
    for (u32 i = 0; i < settings.ends_with_offsets.size(); ++i) {
        if (i != 0) s.append(", ");
        s.append(address_make_string(u64(settings.ends_with_offsets[i]), Process::Arch::NONE));
    }
    s.append("])");
    return s;
};

static constexpr auto hack_scan_tostring = [](Hack::Scan& scan)
{
    string s{"MemoryScan(type="};
    s.append(scan.type_name());
    s.append(", ");
    s.append("begin=");
    s.append(address_make_string(u64(scan.begin), Process::Arch::NONE));
    s.append(", ");
    s.append("size=");
    s.append(std::to_string(scan.size));
    s.append(", ");
    s.append("rwx=");
    s.append(std::to_string(u16(scan.read)));
    s.append(std::to_string(u16(scan.write)));
    s.append(std::to_string(u16(scan.execute)));
    s.append(", ");

    if (scan.type_id() == typeid(string).hash_code()) {
        s.append("regex=");
        s.append(scan.regex ? "True" : "False");
        s.append(", ");
    }

    s.append("threaded=");
    s.append(scan.threaded ? "True" : "False");

    s.append(")");
    return s;
};

//endregion

}

#endif
