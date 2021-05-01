#include <pybind11/pybind11.h>
#include <pybind11/operators.h>
#include <pybind11/stl.h>

#include "Hack.h"
#include "Buffer.h"
#include "Address.h"
#include "Variable.h"
#include "Instruction.h"

using namespace pygamehack;
namespace py = pybind11;
using namespace py::literals;

//region Helpers

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


template<typename T, typename Func>
constexpr void define_class_getitem_pass_type_args_custom(py::class_<T>& cls,  Func&& func)
{
    py::object classmethod = py::globals()["__builtins__"]["classmethod"];
    
    py::cpp_function class_getitem(std::move(func));

    cls.attr("__class_getitem__") = classmethod(class_getitem);
}

template<typename T>
constexpr void define_class_getitem_pass_type_args(py::class_<T>& cls)
{
    define_class_getitem_pass_type_args_custom<T>(cls, 
        [](py::object cls, py::object key){ return py::make_tuple(cls, key); });
}

template<typename T>
void define_python_copy(py::class_<T>& cls)
{
    cls
        .def("__copy__",  [](const T &self) {
            return T(self);
        })
        .def("__deepcopy__", [](const T &self, py::dict) {
            return T(self);
        }, "memo"_a);
}

//endregion

//region Python wrappers - Process

static constexpr auto process_iter = [](py::object& callback)
{
    Process::iter([&callback](const ProcessInfo& info){
        return py::cast<bool>(callback(info));
    });
};

static constexpr auto process_iter_regions = [](Process& self, uptr begin, usize size, py::object& callback, Memory::Protect prot, usize block_size)
{
    py::gil_scoped_release release;
    self.iter_regions(begin, size, [&self, &callback](uptr rbegin, usize rsize, const u8* data) {
        Buffer buffer{ self, (u8*)data, rsize };
        py::gil_scoped_acquire  acquire_gil;
        return py::cast<bool>(callback(rbegin, buffer));
    }, prot, true, block_size);
};

//endregion

//region Python wrappers - Buffer

static constexpr auto buffer_read_from = [](Buffer& self, uptr src, usize size, uptr offset) 
{
    py::gil_scoped_release release;
    return self.read_from(src, size, offset);
};

static constexpr auto buffer_write_to = [](Buffer& self, uptr dst, usize size, uptr offset) 
{
    py::gil_scoped_release release;
    return self.write_to(dst, size, offset);
};

static constexpr auto buffer_read_buffer = [](Buffer& self, uptr offset, Buffer& dst) 
{
    py::gil_scoped_release release;
    return self.read_buffer(offset, dst);
};

static constexpr auto buffer_write_buffer = [](Buffer& self, uptr offset, const Buffer& src) 
{
    py::gil_scoped_release release;
    return self.write_buffer(offset, src);
};

static constexpr auto buffer_read_string = [](Buffer& self, uptr offset, usize size) 
{
    py::gil_scoped_release release;
    return self.read_string(offset, size);
};

static constexpr auto buffer_write_string = [](Buffer& self, uptr offset, const string& data) 
{
    py::gil_scoped_release release;
    return self.write_string(offset, data);
};

//endregion

//region Python wrappers - Hack

static constexpr auto hack_follow = [](Hack& self, uptr begin, const uptr_path& offsets, bool add_first_offset_to_begin) 
{
    py::gil_scoped_release release;
    return self.follow(begin, offsets, add_first_offset_to_begin);
};

static constexpr auto hack_find = [](Hack& self, i8 value, uptr begin, usize size) 
{
    py::gil_scoped_release release;
    return self.find(value, begin, size);
};

static constexpr auto hack_scan_bytes = [](Hack& self, const string& value, uptr begin, usize size, usize max_results, bool regex, bool threaded) 
{
    py::gil_scoped_release release;
    return self.scan(value, begin, size, max_results, regex, threaded);
};

template<typename T>
static auto hack_scan_type(Hack& self, const T& value, uptr begin, usize size, usize max_results, bool threaded) 
{
    py::gil_scoped_release release;
    return self.scan<T>(value, begin, size, max_results, threaded);
}

static constexpr auto hack_read_buffer = [](Hack& self, uptr src, Buffer& dst) 
{
    py::gil_scoped_release release;
    return self.read_buffer(src, dst);
};

static constexpr auto hack_write_buffer = [](Hack& self, uptr dst, const Buffer& src) 
{
    py::gil_scoped_release release;
    return self.write_buffer(dst, src);
};

static constexpr auto hack_read_string = [](Hack& self, uptr src, usize size) 
{
    py::gil_scoped_release release;
    return self.read_string(src, size);
};

static constexpr auto hack_write_string = [](Hack& self, uptr dst, const string& data) 
{
    py::gil_scoped_release release;
    return self.write_string(dst, data);
};

static constexpr auto hack_cheat_engine_load_pointer_scan_file = [](Hack& hack, const string& path, bool threaded)
{
    py::gil_scoped_release release;
    return hack.cheat_engine_load_pointer_scan_file(path, threaded);
};

static constexpr auto hack_cheat_engine_save_pointer_scan_file = [](Hack& hack, const string& path, const Hack::CE::AddressPtrs& addresses, const Hack::CE::Settings& settings, bool single_file)
{
    py::gil_scoped_release release;
    hack.cheat_engine_save_pointer_scan_file(path, addresses, settings, single_file);
};

//endregion

//region Python wrappers - Instruction

static constexpr auto instruction_iter = [](const string& raw_code, bool break_on_return, Instruction::Mode m)
{
    return py::make_iterator(
        InstructionIter(raw_code, m, break_on_return),
        InstructionIter(raw_code, m, break_on_return, UINT32_MAX)
    );
};

static constexpr auto instruction_extract_searchable_bytes = [](const string& raw_code, usize last_instruction_offset)
{
    auto [code, offset, size] = Instruction::extract_searchable_bytes(raw_code, last_instruction_offset);
    return py::make_tuple(py::bytes(code), offset, size);
};

//endregion

//region Python wrappers - ToString

template<typename T>
struct TypeName { const char* operator()() const noexcept { return ""; } };

#define F(T, name) template<> struct TypeName<T> { const char* operator()() const noexcept { return name; } };

F(Buffer, "buf")
F(PtrToBuffer, "p_buf")
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

//endregion

//region Define funcs

void define_process(py::module& m)
{
    py::class_<Memory>(m, "UnsafeProtectableMemoryContextManager")
        .def("__enter__", [](Memory& self, py::args a, py::kwargs kw){ self.protect(); })
        .def("__exit__", [](Memory& self, py::args a, py::kwargs kw){ self.reset(); });

    py::class_<ProcessInfo>(m, "ProcessInfo")
        .def_readwrite("name", &ProcessInfo::name)
        .def_readwrite("id", &ProcessInfo::id)
        .def_readwrite("parent_id", &ProcessInfo::parent_id)
        .def_readwrite("size", &ProcessInfo::size)
        .def_readwrite("thread_count", &ProcessInfo::thread_count);

    py::class_<Process> proc_class(m, "Process");

    py::enum_<Process::Arch>(proc_class, "Arch")
        .value("x86", Process::Arch::X86)
        .value("x64", Process::Arch::X64)
        .value("NONE", Process::Arch::NONE)
        .export_values();

    py::enum_<Memory::Protect>(proc_class, "Protect", py::arithmetic())
        .value("NoAccess", Memory::Protect::NO_ACCESS)
        .value("ReadOnly", Memory::Protect::READ_ONLY)
        .value("ReadWrite", Memory::Protect::READ_WRITE)
        .value("WriteCopy", Memory::Protect::WRITE_COPY)
        .value("Execute", Memory::Protect::EXECUTE)
        .value("ExecuteRead", Memory::Protect::EXECUTE_READ)
        .value("ExecuteReadWrite", Memory::Protect::EXECUTE_READ_WRITE)
        .value("ExecuteWriteCopy", Memory::Protect::EXECUTE_WRITE_COPY)
        .value("Guard", Memory::Protect::GUARD)
        .value("NoCache", Memory::Protect::NO_CACHE)
        .value("WriteCombine", Memory::Protect::WRITE_COMBINE)
        .export_values();

    proc_class    
        .def("__repr__", process_tostring)

        .def_property_readonly(
            "arch", &Process::arch,
                "The architechture of the attached process (32/64 bit)")
        
        .def_property_readonly(
            "pid", &Process::pid,
                "The process id the attached process")
        
        .def_property_readonly(
            "modules", &Process::modules,
                "A map of the currently loaded dynamic modules (name: (begin, size))")
        
        .def_property_readonly(
            "attached", &Process::is_attached,
                "Is the instance attached to a running process")

        .def_property_readonly(
            "ptr_size", &Process::get_ptr_size,
                "Size of a pointer in bytes in the target process")

        .def_property_readonly(
            "max_ptr", &Process::get_max_ptr,
                "The maximum value that a pointer can hold in the target process")

        .def(
            "get_base_address", &Process::get_base_address, 
                "Get the base address of a given DLL module", 
                "module_name"_a)
                
        .def(
            "iter_regions", process_iter_regions,
                "Iterate over the memory regions in the process", 
                "begin"_a, "size"_a, "callback"_a, "protect"_a=Memory::Protect::NONE, "block_size"_a=4096u)
                
        .def(
            "protect", &Process::protect,
                "", 
                "begin"_a, "size"_a, "protect"_a=Memory::Protect::READ_WRITE)
        
        .def_static(
            "iter", process_iter,
                "Iterate over all running processes")
        
        .def_static(
            "kill", &Process::kill,
                "Kill a process with the given id if it is running",
                "process_id"_a)
        
        .def_static(
            "created_at", &Process::created_at,
                "Returns the time at which a process was created in terms of time since epoch",
                "process_id"_a)
        
        .def_static(
            "entry_point", &Process::entry_point,
                "Returns the address of the program entry point located in the PE header",
                "executable_name"_a);
}


void define_address(py::module& m)
{
    py::class_<Address> address_class(m, "Address");

    define_python_copy<Address>(address_class);
    address_class.attr("UpdateAll") = Address::UPDATE_ALL;

    py::enum_<Address::Type>(address_class, "Type")
        .value("Manual", Address::Type::MANUAL)
        .value("Static", Address::Type::STATIC)
        .value("Dynamic", Address::Type::DYNAMIC)
        .export_values();

    address_class
        .def("__repr__", address_tostring)

        .def(
            py::init(&Address::Manual), py::keep_alive<2, 1>(),
                "Create a manual address with the given value",
                "hack"_a, "address"_a)

        .def(
            py::init(&Address::Static), py::keep_alive<2, 1>(),
                "Create a static address from the given module and offset",
                "hack"_a, "module_name"_a, "offset"_a)

        .def(
            py::init(&Address::Dynamic), py::keep_alive<2, 1>(),
                "Create a dynamic address from the given parent address and offset path. " \
                "If 'add_first_offset_to_parent_address' is 'True', then the first offset in the path will be added to the parent address before the first read." \
                "Otherwise the parent address is read first and the first offset in the path is added to the resulting address read from the parent address.",
                "parent"_a, "offsets"_a, "add_first_offset_to_parent_address"_a=true)

        .def_property_readonly(
            "hack", &Address::hack, py::return_value_policy::reference,
                "The hack instance that this address belongs to")

        .def_property_readonly(
            "loaded", &Address::loaded,
                "Has the address been loaded")

        .def_property_readonly(
            "type", &Address::type,
                "Type of the address (MANUAL, STATIC, DYNAMIC). This controls how the address will be loaded.")

        .def_property_readonly(
            "valid", &Address::valid,
                "Whether the address points to a valid memory region in the target process")

        .def_property_readonly(
            "value", &Address::value,
                "Value of the address")
                
        .def_property_readonly(
            "parent", &Address::parent, py::return_value_policy::reference,
                "The parent address of this address (only for DYNAMIC addresses)")

        .def_property_readonly(
            "offsets", &Address::offsets,
                "The offset path followed to reach this address (only for DYNAMIC addresses)")
        
        .def_property_readonly(
            "module_name", &Address::module_name,
                "The name of the module from which this address derives its base (only for STATIC addresses)")
          
        .def_property_readonly(
            "module_offset", &Address::module_offset,
                "The offset into the module associated to this address (only for STATIC addresses)")
          
        .def_property(
            "name", &Address::name, &Address::set_name,
                "The name of this address")
                      
        .def(
            "load", &Address::load,
                "Load the value of the address. For manual addresses this is a no-op. Returns the loaded address.")

       .def(
            "auto_update", &Address::auto_update, py::return_value_policy::reference,
                "Turn on automatic loading for this address. " \
                "When turned on, each time Hack.update() is called, this address will be reloaded.\n"\
                "You can conditionally load addresses by calling 'set_update_mask'. ")

        .def(
            "stop_auto_update", &Address::stop_auto_update,
                "Turn off automatic loading for this address.")

        .def(
            "set_update_mask", &Address::set_update_mask,
                "Set the mask used to determine whether this address will be loaded or not." \
                "An address is loaded if (Hack.update_mask() & Address.update_mask()) != 0.\n" \
                "NOTE: You cannot access Address.update_mask(), it is just provided for clarity (it is a private member).",
                "mask"_a = Address::UPDATE_ALL)

        .def(
            "add_offsets", &Address::add_offsets,
                "Add a list of offsets to the current offset path of the address. This affects how the address will be loaded (only for DYNAMIC addresses).",
                "offsets"_a)
                
        .def(
            "pop_offsets", &Address::pop_offsets,
                "Pop the given number of offsets from the end of the current offset path of the address. If n=0 then all offsets will be popped. This affects how the address will be loaded (only for DYNAMIC addresses).",
                "n"_a=0u)

        .def_static(
            "make_string", address_make_string,
                "Convert a numberic address to a normalized hexadecimal string",
                "value"_a, "arch"_a=Process::Arch::NONE);
}


void define_buffer(py::module& m)
{    
    py::class_<Buffer> buffer_class(m, "Buffer", py::buffer_protocol());
    
    define_python_copy<Buffer>(buffer_class);

    buffer_class.def_buffer([](Buffer &b) -> py::buffer_info {
        return py::buffer_info(
            b.data(),                                // Pointer to buffer
            { py::ssize_t(b.size()) },               // Buffer dimensions
            { 1 }                                    // Stride (in bytes) for each dimension
        );
     });

    buffer_class
        .def("__repr__", buffer_tostring)
        
        .def(
            py::init<Hack&, usize>(), py::keep_alive<2, 1>(),
                "Create a buffer of a given size", 
                "Hack"_a, "size"_a)

        .def(
            py::init<Buffer&, uptr, usize>(), py::keep_alive<2, 1>(),
                "Create a view into another buffer of the given size starting at the given offset",
                "src"_a, "offset"_a, "size"_a)

        .def_property_readonly(
            "size", &Buffer::size,
                "Size of the buffer in bytes")

        .def(
            "clear", &Buffer::clear,
                "Set all bytes to 0")

        .def(
            "resize", &Buffer::resize,
                "Resize the buffer to the given size in bytes",
                "size"_a)

        .def(
            "read_from", buffer_read_from,
                "Read the given number of bytes from the memory at the given address into the buffer at the given offset",
                "src"_a, "size"_a=0, "offset"_a=0u)

        .def(
            "write_to", buffer_write_to,
                "Write the given number of bytes to the memory at the given address from the buffer at the given offset",
                "dst"_a, "size"_a=0, "offset"_a=0u)
                             
        .def(
            "read_buffer", buffer_read_buffer,
                "Read the contents of the buffer at the given offset into the given buffer",
                "offset"_a, "dst_buffer"_a)

        .def(
            "write_buffer", buffer_write_buffer,
                "Write the contents of the given buffer into the buffer at the given offset",
                "offset"_a, "src_buffer"_a)

        .def(
            "read_ptr", &Buffer::read_ptr,
                "Read a pointer from this buffer at the given offset",
                "offset"_a)

        .def(
            "write_ptr", &Buffer::write_ptr,
                "Write a pointer to this buffer at the given offset",
                "offset"_a, "ptr"_a)

        .def(
            "read_usize", &Buffer::read_ptr,
                "Read a native_size_type from this buffer at the given offset",
                "offset"_a)

        .def(
            "write_usize", &Buffer::write_ptr,
                "Write a native_size_type to this buffer at the given offset",
                "offset"_a, "v"_a)

        .def(
            "read_string", buffer_read_string,
                "Read the contents of the buffer at the given offset as a string of the given size. If size=0, the buffer is read until the end.",
                "offset"_a=0u, "size"_a=0u)

        .def(
            "write_string", buffer_write_string,
                "Write the contents of the given string into the buffer at the given offset. If the buffer is too small, the string is truncated.",
                "offset"_a, "data"_a)

        .def(
            "read_bytes", [](Buffer& self, uptr offset, usize size) { return py::bytes(buffer_read_string(self, offset, size)); },
                "Read the contents of the buffer at the given offset as a byte-string of the given size. If size=0, the buffer is read until the end.",
                "offset"_a=0u, "size"_a=0u)
                
        .def(
            "strlen", &Buffer::strlen,
                "Count the number of non-null bytes starting at the given offset. Works the same as 'strnlen_s' in C.",
                "offset"_a=0u);

    #define F(type, name) \
    buffer_class \
        .def( \
            "read_" name, &Buffer::read_value<type>, \
                "Read a " name " from this buffer at the given offset", \
                "offset"_a)\
        .def( \
            "write_" name, &Buffer::write_value<type>, \
                "Write a " name " to this buffer at the given offset",  \
                "offset"_a, "value"_a);
    
    FOR_EACH_INT_TYPE(F)
    
    #undef F
    
    buffer_class
        .def(py::self == py::self)
        .def(py::self != py::self);
}


void define_hack(py::module& m)
{
    py::class_<Hack::CE::Settings>(m, "CheatEnginePointerScanSettings")
        .def(py::init<>())
        .def("__repr__", hack_cheat_engine_settings_tostring)
        .def_readwrite("max_level", &Hack::CE::Settings::max_level,
            "Maximum number of offsets per pointer-scan result (default: 7)")
        .def_readwrite("max_offset", &Hack::CE::Settings::max_offset,
            "Maximum value that any offset can have (default: 4095)")
        .def_readwrite("is_compressed", &Hack::CE::Settings::is_compressed,
            "Save the pointer-scan in a compressed format (default: True)")
        .def_readwrite("is_aligned", &Hack::CE::Settings::is_aligned,
            "All offsets are 32-byte alligned (default: True)")
        .def_readwrite("ends_with_offsets", &Hack::CE::Settings::ends_with_offsets,
            "List of offsets that every address must end with. (default: [])");
    
    auto& hack_class = py::class_<Hack>(m, "Hack");

    hack_class
        .def("__repr__", hack_tostring)

        .def(py::init<>())
        
        .def_property_readonly(
            "process", &Hack::process,
                "The process used by the hack")
        
        .def(
            "attach", (void(Hack::*)(u32))&Hack::attach,
                "Attach to a process with the given process id",
                "process_id"_a)

      .def(
            "attach", (void(Hack::*)(const string&))&Hack::attach,
                "Attach to a process with the given process name",
                "process_name"_a)

        .def(
            "detach", &Hack::detach, 
                "Detach from the currently attached process")
                  
        .def(
            "follow", hack_follow, 
                "Follow a pointer path starting at the given pointer 'begin' with the given offsets.\n" \
                "If add_first_offset_to_begin=True, then the first offset in the path will be added to 'begin' before reading, otherwise 'begin' is read before the first offset is added.", 
                "begin"_a, "offsets"_a, "add_first_offset_to_begin"_a=true)
    
        .def(
            "find", hack_find, 
                "Scan for the given byte in a small memory region starting at 'begin' and spanning 'size' bytes." \
                "If the value is not found, then '0' is returned, otherwise the address of the value is returned",
                "value"_a, "begin"_a, "size"_a = 1000u)
            
        .def(
            "scan", hack_scan_bytes, 
                "Scan for the given bytes in memory starting at 'begin' and spanning 'size' bytes up to the given max_results.\n" \
                "If 'regex' is true, then a regex-search will be used for scanning, otherwise will scan for an exact byte-copy of value." \
                "If 'threaded' is true and the scan is large enough to be worth threading, then a multi-threaded scan will be performed.",
                "value"_a, "begin"_a, "size"_a, "max_results"_a=0, "regex"_a=false, "threaded"_a=true)
   
        .def(
            "read_buffer", hack_read_buffer,
                "Read the contents of memory at the given address into the given buffer",
                "src"_a, "dst_buffer"_a)

        .def(
            "write_buffer", hack_write_buffer,
                "Write the contents of the given buffer into memory at the given address",
                "dst"_a, "src_buffer"_a)
                
        .def(
            "read_ptr", &Hack::read_ptr,
                "Read a pointer from memory at the given address",
                "src"_a)

        .def(
            "write_ptr", &Hack::write_ptr,
                "Write a pointer into memory at the given address",
                "dst"_a, "ptr"_a)

        .def(
            "read_usize", &Hack::read_ptr,
                "Read a native size type from memory at the given address",
                "src"_a)

        .def(
            "write_usize", &Hack::write_ptr,
                "Write a native size type into memory at the given address",
                "dst"_a, "value"_a)

        .def(
            "read_string", hack_read_string, 
                "Read the contents of memory at the given address as a string of the given size",
                "src"_a, "size"_a)

        .def(
            "write_string", hack_write_string, 
                "Write the contents of the given string into memory at the given address",
                "dst"_a, "data"_a)

        .def(
            "read_bytes", [](Hack& self, uptr src, usize size) { return py::bytes(hack_read_string(self, src, size)); },
                "Read the contents of memory at the given address as a byte-string of the given size",
                "src"_a, "size"_a)
                
        .def(
            "cheat_engine_load_pointer_scan_file", hack_cheat_engine_load_pointer_scan_file,
                "Load a CheatEngine PointerScan file from the given path into a list of addresses and corresponding settings for the file.\n" \
                "If 'threaded' is true then the pointer scan results will be loaded with multiple threads (this is unnecessary for a small number of results (<256)).\n" \
                "Returns tuple(addresses, settings).",
                "path"_a, "threaded"_a=true)

        .def(
            "cheat_engine_save_pointer_scan_file", hack_cheat_engine_save_pointer_scan_file,
                "Save a list of addresses as a CheatEngine PointerScan file to the given path with the given settings.\n" \
                "If 'single_file' is true then it will save all of the pointer scan results into a single file.",
                "path"_a, "addresses"_a, "settings"_a=Hack::CE::Settings{}, "single_file"_a=true);

    
    #define F(type, name) \
    hack_class \
        .def( \
            "scan_" name, hack_scan_type<type>, \
                "Scan for a " name " in memory starting at the given address in the given range up to the given max-results. If max-results=0 then all results will be returned." \
                "If 'threaded' is true and the scan is large enough to be worth threading, then a multi-threaded scan will be performed.", \
                "value"_a, "begin"_a, "size"_a, "max_results"_a=0, "threaded"_a=true)\
        .def( \
            "read_" name, &Hack::read_value<type>, \
                "Read a " name " from the given address", \
                "address"_a)\
        .def( \
            "write_" name, &Hack::write_value<type>, \
                "Write a " name " to the given address",  \
                "address"_a, "value"_a);

    FOR_EACH_INT_TYPE(F)
    #undef F
}


template<typename T, usize N>
void define_variable(py::module& m, const char(&type_name)[N])
{
    py::class_<Variable<T>> variable_class(m, type_name);

    if constexpr(!std::is_same_v<T, string> && !std::is_same_v<T, Ptr>) {
        variable_class.attr("size") = sizeof(T);
    }

    if constexpr(std::is_same_v<T, Ptr>) {
        variable_class.attr("Tag") = Ptr::TAG;
        define_class_getitem_pass_type_args_custom<Variable<T>>(variable_class,
            [](py::object cls, py::object key){ return py::make_tuple(key, Ptr::TAG); });
    }

    variable_class
        .def("__repr__", variable_tostring<T>)

        .def(
            py::init<Address&>(), py::keep_alive<2, 1>(),
                "Create a variable from the given address",
                "address"_a)

        .def_property_readonly(
            "address", &Variable<T>::address, py::return_value_policy::reference,
                "Return the address associated to this variable")

        .def(
            "get", &Variable<T>::get,
                "Return the stored variable")

        .def(
            "read", &Variable<T>::read,
                "Read into local storage from the memory at the address of this variable and return the stored variable")

        .def(
            "write", &Variable<T>::write,
                "Write to local storage and to the memory at the address of this variable from the given value",
                "value"_a)

        .def(
            "reset", &Variable<T>::reset,
                "Reset the value of the local storage to the default value when originally constructed");

    // if constexpr(std::is_same_v<T, string>) {
    //     variable_class
    //         .def_property_readonly(
    //             "length", &Variable<string>::size,
    //                 "Return the length of the stored string")
    //         .def(
    //             "resize", &Variable<string>::resize,
    //                 "Resize the stored string",
    //                 "size"_a);
    // }
}


template<typename T, usize N>
void define_variable_buffer(py::module& m, const char(&type_name)[N])
{
    py::class_<T> variable_class(m, type_name, py::buffer_protocol());

    define_class_getitem_pass_type_args<T>(variable_class);

    variable_class.def_buffer([](T &v) -> py::buffer_info {
        return py::buffer_info(
            v.get().data(),                          // Pointer to buffer
            { py::ssize_t(v.get().size()) },         // Buffer dimensions
            { 1 }                                    // Stride (in bytes) for each dimension
        );
     });

    variable_class
        .def("__repr__", variable_tostring<T>)

        .def(
            py::init<Address&, usize>(), py::keep_alive<2, 1>(),
                "Create a buffer variable of the given size from the given address",
                "address"_a, "size"_a)

       .def(
            py::init<T&, uptr, usize>(), py::keep_alive<2, 1>(),
                "Create a buffer view variable of the given size from the given parent buffer",
                "parent"_a, "offset"_a, "size"_a)

        .def_property_readonly(
            "address", &T::address, py::return_value_policy::reference,
                "Return the address associated to this variable")

        .def_property_readonly(
            "is_view", &T::is_view,
                "Is this variable a view into another variable")

        .def_property_readonly(
            "offset_in_parent", &T::offset_in_parent,
                "Return the offset of this variables address with respect to the parent variable")

        .def_property_readonly(
            "parent", &T::parent, py::return_value_policy::reference,
                "Return the parent variable if this variable is a buffer view. Raises error for non-view variables.")

        .def(
            "get", &T::get, py::return_value_policy::reference,
                "Return the stored buffer")

        .def(
            "read", &T::read, py::return_value_policy::reference,
                "Read into local storage from the memory at the address of this variable and return the stored buffer. If size=0, the entire buffer is read.",
                "offset"_a=0, "size"_a=0)

        .def(
            "write", &T::write,
                "Write to local storage at the given offset from the given buffer",
                "value"_a, "offset"_a=0u)

        .def(
            "flush", &T::flush,
                "Write to the memory at the address of this variable from local storage. If size=0, the entire buffer is written.",
                "offset"_a=0, "size"_a=0)

        .def(
            "reset", &T::reset,
                "Clear the memory of the local storage buffer");

}


void define_variables(py::module& m)
{   
    define_variable<Ptr>(m, "ptr");
    // define_variable<string>(m, "str");
    define_variable_buffer<VariableBuffer>(m, "buf");
    define_variable_buffer<VariablePtrToBuffer>(m, "p_buf");

    #define F(type, name) define_variable<type>(m, name);
    FOR_EACH_INT_TYPE(F)
    #undef F

    m.attr("int") = m.attr("i32");
    m.attr("uint") = m.attr("u32");
    m.attr("usize") = m.attr("ptr");
}


void define_instruction(py::module& m)
{
    py::class_<Operand> op_class(m, "Operand");
    
    op_class
        .def_readwrite("type", &Operand::type, "Operand type (register, memory, etc)")
        .def_readwrite("reg", &Operand::reg, "Register (if any)")
        .def_readwrite("basereg", &Operand::basereg, "Base register (if any)")
        .def_readwrite("indexreg", &Operand::indexreg, "Index register (if any)")
        .def_readwrite("scale", &Operand::scale, "Scale (if any)")
        .def_readwrite("dispbytes", &Operand::dispbytes, "Displacement bytes (0 = no displacement)")
        .def_readwrite("dispoffset", &Operand::dispoffset, "Displacement value offset")
        .def_readwrite("immbytes", &Operand::immbytes, "Immediate bytes (0 = no immediate)")
        .def_readwrite("immoffset", &Operand::immoffset, "Immediate value offset")
        .def_readwrite("sectionbytes", &Operand::sectionbytes, "Section prefix bytes (0 = no section prefix)")
        .def_readwrite("section", &Operand::section, "Section prefix value")
        .def_readwrite("displacement", &Operand::displacement, "Displacement value")
        .def_readwrite("immediate", &Operand::immediate, "Immediate value")
        .def_readwrite("flags", &Operand::flags, "Operand flags");
        
    py::class_<Instruction> inst_class(m, "Instruction");
    
    inst_class.attr("Operand") = op_class;

    py::enum_<Instruction::Type> inst_type(inst_class, "Type");
    FOR_EACH_INSTRUCTION_TYPE([&](Instruction::Type t, const char* name){ inst_type.value(name, t); })
    inst_type.export_values();

    py::enum_<Instruction::Mode>(inst_class, "Mode")
        .value("M32", Instruction::Mode::M32)
        .value("M16", Instruction::Mode::M16)
        .export_values();

    py::enum_<Instruction::Format>(inst_class, "Format")
        .value("ATT", Instruction::Format::ATT)
        .value("INTEL", Instruction::Format::INTEL)
        .export_values();

    inst_class
        .def_readwrite("length", &Instruction::length, "Instruction length")
        .def_readwrite("type", &Instruction::type, "Instruction type")
        .def_readwrite("mode", &Instruction::mode, "Addressing mode")
        .def_readwrite("opcode", &Instruction::opcode, "Actual opcode")
        .def_readwrite("modrm", &Instruction::modrm, "MODRM byte")
        .def_readwrite("sib", &Instruction::sib, "SIB byte")
        .def_readwrite("modrm_offset", &Instruction::modrm_offset, "MODRM byte offset")
        .def_readwrite("extindex", &Instruction::extindex, "Extension table index")
        .def_readwrite("fpuindex", &Instruction::fpuindex, "FPU table index")
        .def_readwrite("dispbytes", &Instruction::dispbytes, "Displacement bytes (0 = no displacement)")
        .def_readwrite("immbytes", &Instruction::immbytes, "Immediate bytes (0 = no immediate)")
        .def_readwrite("sectionbytes", &Instruction::sectionbytes, "Section prefix bytes (0 = no section prefix)")
        .def_readwrite("op1", &Instruction::op1, "First operand (if any)")
        .def_readwrite("op2", &Instruction::op2, "Second operand (if any)")
        .def_readwrite("op3", &Instruction::op3, "Additional operand (if any)")
        .def_readwrite("flags", &Instruction::flags, "Instruction flags")
        .def_readwrite("eflags_affected", &Instruction::eflags_affected, "Processor eflags affected")
        .def_readwrite("eflags_used", &Instruction::eflags_used, "Processor eflags used by this instruction")
        .def_readwrite("iop_written", &Instruction::iop_written, "Mask of affected implied registers (written)")
        .def_readwrite("iop_read", &Instruction::iop_read, "Mask of affected implied registers (read)")
        
        .def(
            "__repr__", instruction_tostring)

        .def(
            "to_string", &Instruction::to_string,
                "Convert Instruction object into a readable assembly string", 
                "fmt"_a = Instruction::Format::ATT)
        
        .def_static(
            "from_string", &Instruction::from_string,
                "Disassemble code from raw bytes into an Instruction object",
                "raw_code"_a, "mode"_a = Instruction::Mode::M32)
                
        .def_static(
            "to_readable_code", &Instruction::to_readable_code,
                "Disassemble code from raw bytes into a readable string of instructions",
                "raw_code"_a, "fmt"_a = Instruction::Format::ATT, "mode"_a = Instruction::Mode::M32)
                
        .def_static(
            "extract_searchable_bytes", instruction_extract_searchable_bytes,
                "Disassemble code from raw bytes into a readable string of instructions",
                "raw_code"_a, "last_instruction_offset"_a = UINT32_MAX)
        
        .def_static(
            "iter", instruction_iter, py::keep_alive<0, 1>(), /* keep string alive while iterating */
                "Iterate instructions from a raw code string",
                "raw_code"_a, "break_on_return"_a=true, "mode"_a=Instruction::Mode::M32);
}

//endregion


PYBIND11_MODULE(cpygamehack, m)
{
    m.attr("__version__") = "1.0";

    define_process(m);
    
    define_address(m);

    define_buffer(m);

    define_hack(m);

    define_variables(m);

    define_instruction(m);
}
