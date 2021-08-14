#include "PyVariableArray.h"
#include "pywrappers.h"
#include "pytostring.h"

using namespace pygamehack;
namespace py = pybind11;
using namespace py::literals;


//region Define funcs

void define_process(py::module& m)
{
    py::class_<Memory>(m, "UnsafeProtectableMemoryContextManager")
        .def("__enter__", [](Memory& self, py::args a, py::kwargs kw){ self.protect(); })
        .def("__exit__", [](Memory& self, py::args a, py::kwargs kw){ self.reset(); });

    py::class_<ProcessInfo>(m, "ProcessInfo")
        .def("__str__", process_info_tostring)
        .def("__repr__", process_info_tostring)
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
        .def("__str__", process_tostring)

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
            "read_only", &Process::is_read_only,
                "Is the process open in read-only mode")

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
            "follow", process_follow,
                "Follow a pointer path starting at the given pointer 'begin' with the given offsets.\n" \
                "NOTE: the first offset in the path will be added to 'begin' before reading.",
                "begin"_a, "offsets"_a)

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
        .def("__str__", address_tostring)

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
        .def("__str__", buffer_tostring)
        
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
            "read_string", buffer_read_dynamic_string,
                "Read the contents of the buffer at the given offset as a string of the given size. \n"
                "If size=0, the buffer is read until the first null byte, or until the end of the buffer, whichever comes first.",
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


void define_hack_scan(py::module& m)
{
    py::class_<Hack::Scan> scan_class(m, "MemoryScan");

    scan_class
        .def("__str__", hack_scan_tostring)

        .def_static("str", [](const string& v, uptr b, usize s, usize m, bool r, bool w, bool e, bool rx, bool t){ return Hack::Scan(v, b, s, m, r, w, e, rx, t); },
                "value"_a, "begin"_a, "size"_a, py::kw_only(), "max_results"_a=0,
                "read"_a=true, "write"_a=false, "execute"_a=false,
                "regex"_a=false, "threaded"_a=true)

        .def_readwrite("begin", &Hack::Scan::begin,
            "The start address of the memory region to scan")

        .def_readwrite("size", &Hack::Scan::size,
            "The size of the memory region to scan")

        .def_readwrite("max_results", &Hack::Scan::max_results,
            "The maximum number of results returned by the scan (default: 0)")

        .def_readwrite("read", &Hack::Scan::read,
            "(default: True)")

        .def_readwrite("write", &Hack::Scan::write,
            "(default: False)")

        .def_readwrite("execute", &Hack::Scan::execute,
            "(default: False)")

        .def_property_readonly ("regex", [](Hack::Scan& s){ return s.regex; },
            "If 'regex' is true, then a regex-search will be used for scanning, otherwise will scan for an exact byte-copy of value (default: False).\n"
            "NOTE: You can only set 'regex=True' when scanning for strings/bytes.")

        .def_readwrite("threaded", &Hack::Scan::threaded,
            "If 'threaded' is true and the scan is large enough to be worth threading, then a multi-threaded scan will be performed (default: True)")

        .def(
            "set_value", hack_scan_set_value,
                "Set the next value to be scanned for in the scan-modify loop",
                "value"_a);

    #define F(type, name) scan_class \
        .def_static(name, [](type v, uptr b, usize s, usize m, bool r, bool w, bool e, bool t){ return Hack::Scan(v, b, s, m, r, w, e, t); }, \
            "value"_a, "begin"_a, "size"_a, py::kw_only(), "max_results"_a=0, \
            "read"_a=true, "write"_a=false, "execute"_a=false, "threaded"_a=true);
    FOR_EACH_INT_TYPE(F)
    #undef F
}


void define_hack_cheat_engine(py::module& m)
{
    py::class_<Hack::CE::Settings>(m, "CheatEnginePointerScanSettings")
        .def(py::init<>())
        .def("__str__", hack_cheat_engine_settings_tostring)
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
}


void define_hack(py::module& m)
{
    define_hack_scan(m);

    define_hack_cheat_engine(m);

    // Hack
    auto& hack_class = py::class_<Hack>(m, "Hack");

    hack_class
        .def("__str__", hack_tostring)

        .def(py::init<>())
        
        .def_property_readonly(
            "process", &Hack::process,
                "The process used by the hack")
        
        .def(
            "attach", (bool(Hack::*)(u32, bool))&Hack::attach,
                "Attach to a process with the given process id",
                "process_id"_a, py::kw_only(), "read_only"_a=false)

      .def(
            "attach", (bool(Hack::*)(const string&, bool))&Hack::attach,
                "Attach to a process with the given process name",
                "process_name"_a, py::kw_only(), "read_only"_a=false)

        .def(
            "detach", &Hack::detach, 
                "Detach from the currently attached process")

        .def(
            "find", hack_find, 
                "Scan for the given byte in a small memory region starting at 'begin' and spanning 'size' bytes." \
                "If the value is not found, then '0' is returned, otherwise the address of the value is returned",
                "value"_a, "begin"_a, "size"_a = 1000u)

        .def(
            "strlen", [](Hack& self, uptr begin, usize size){ return hack_find(self, 0, begin, size); },
                "Scan for a null byte in a small memory region starting at 'begin' and spanning 'size' bytes." \
                "If the value is not found, then '0' is returned, otherwise the address of the value is returned",
                "begin"_a, "max_len"_a = 1000u)

       .def(
            "scan", hack_scan,
                "Scan for the given bytes in memory. See 'MemoryScan' for details.",
                "scan"_a)

       .def(
            "scan_modify", hack_scan_modify,
                "Scan in a loop filtering results at every step by the value set in the previous step. See 'MemoryScan' for details.",
                "scan"_a, "modify_func"_a)

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
            "read_string", hack_read_dynamic_string,
                "Read the contents of memory at the given address as a string of the given size.\n"
                "If 'size=0', then will read until the first null byte, up to a maximum of 'max_len' number of bytes.",
                "src"_a, "size"_a=0u, "max_len"_a=1000u)

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


template<typename Var>
void define_const_variable(py::module& m, const char* type_name)
{
    static constexpr auto do_fail = [](){ throw std::exception{"Cannot write to a constant variable"}; };

    struct Derived : public Var { using Var::Var; };

    py::class_<Derived, Var>(m, type_name)
        .def("flush", [](Derived& v){ do_fail(); })
        .def("write", [](Derived& v, py::object&){ do_fail(); })
        .def("__setitem__", [](Derived& v, py::object&, py::object&){ do_fail(); });
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
        .def("__str__", variable_tostring<T>)

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
}


template<typename T, usize N>
void define_variable_buffer(py::module& m, const char(&type_name)[N])
{
    py::class_<T> variable_class(m, type_name, py::buffer_protocol());

    define_class_getitem_pass_type_args_custom<T>(variable_class, [](py::object cls, py::object key){
        PGH_ASSERT(py::isinstance<py::int_>(key), "You must provide size for a buffer definition: buf[SIZE: int]");
        return py::make_tuple(cls, key);
    });

    variable_class.def_buffer([](T &v) -> py::buffer_info {
        return py::buffer_info(
            v.get().data(),                          // Pointer to buffer
            { py::ssize_t(v.get().size()) },         // Buffer dimensions
            { 1 }                                    // Stride (in bytes) for each dimension
        );
     });

    variable_class
        .def("__str__", variable_tostring<typename T::T>)

        .def(
            py::init<Address&, usize>(), py::keep_alive<2, 1>(),
                "Create a buffer variable of the given size from the given address",
                "address"_a, "size"_a)

        .def(
            py::init<T&, uptr, usize>(), py::keep_alive<2, 1>(),
                "Create a buffer view variable of the given size from the given parent buffer",
                "parent"_a, "offset"_a, "size"_a)

        .def(
            py::init([](PyVariableArray& parent, uptr offset, usize size){ return T((VariableBufferBase&)parent, offset, size); }), py::keep_alive<2, 1>(),
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
                "size"_a=0, "offset"_a=0)

        .def(
            "write", &T::write,
                "Write to local storage at the given offset from the given buffer",
                "value"_a, "offset"_a=0u)

        .def(
            "flush", &T::flush,
                "Write to the memory at the address of this variable from local storage. If size=0, the entire buffer is written.",
                "size"_a=0, "offset"_a=0)

        .def(
            "reset", &T::reset,
                "Clear the memory of the local storage buffer");


     if constexpr(std::is_same_v<T, VariableString>) {
         variable_class
             .def("__len__", &VariableString::strlen)
             .def("__iter__", [](VariableString& v){ return py::make_iterator((const char*)v.get().data(), (const char*)(v.get().data() + v.get().size())); }, py::keep_alive<0, 1>())
             .def("__contains__", [](VariableString& v, const string& s){ return v.get_view().find(s) != string::npos; })
             .def("__reversed__", [](VariableString& v, const string& s){ return string{v.get_view().rbegin(), v.get_view().rend()}; })
             .def("__setitem__", [](VariableString& v, usize n, const string& s){ if (n >= s.size()) throw py::index_error(); v.get().data()[n] = s[0]; })
             .def("__getitem__", [](VariableString& v, usize n){ if (n >= v.size()) throw py::index_error(); return string{(const char*)(v.get().data() + n), 1}; })
             .def("__getitem__", [](VariableString& v, py::slice slice){
                 py::ssize_t start, stop, step, slicelength;
                 if (!slice.compute(v.size(), &start, &stop, &step, &slicelength))
                 throw py::error_already_set();
                 return v.slice(start, stop, static_cast<i64>(step));
             });

         string const_name = "c_" + string{type_name};
         define_const_variable<VariableString>(m, const_name.c_str());
     }
}


template<typename T, usize N>
void define_variable_array(py::module& m, const char(&type_name)[N])
{
    py::class_<T> variable_class(m, type_name, py::buffer_protocol());

    define_class_getitem_pass_type_args_custom<T>(variable_class, [](py::object cls, py::object key){
        // TODO: Assert array getitem args are correct
        PGH_ASSERT(py::isinstance<py::tuple>(key), "You must provide both the type and size for an array definition: arr[TYPE: type, SIZE: int]");
        auto key_t = py::cast<py::tuple>(key);
        PGH_ASSERT(py::len(key) == 2, "You must provide both the type and size for an array definition: arr[TYPE: type, SIZE: int]");
//        PGH_ASSERT(py::isinstance<py::type>(key_t[0]), "You must provide both the type and size for an array definition: arr[TYPE: type, SIZE: int]");
        PGH_ASSERT(py::isinstance<py::int_>(key_t[1]), "You must provide both the type and size for an array definition: arr[TYPE: type, SIZE: int]");
        py::tuple tup(3);
        tup[0] = cls;
        tup[1] = key_t[0];
        tup[2] = key_t[1];
        return tup;
    });

    variable_class.def_buffer([](T &v) -> py::buffer_info {
        return py::buffer_info(
            v.buffer().data(),                       // Pointer to buffer
            { py::ssize_t(v.buffer().size()) },      // Buffer dimensions
            { 1 }                                    // Stride (in bytes) for each dimension
        );
     });

     variable_class
        .def(
            py::init(&T::create),
                "Create a array variable of the given size",
                "address"_a, "size"_a)

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
                "Read into local storage from the memory at the address of this variable and return the stored buffer. If n=0, the entire array is read.",
                "n"_a=0, "starting_at"_a=0)

        .def(
            "write", &T::write,
                "Write the given values to local storage starting at the given position",
                "values"_a, "starting_at"_a=0u)

        .def(
            "flush", &T::flush,
                "Write to the memory at the address of this variable from local storage. If n=0, the entire array is written.",
                "n"_a=0, "starting_at"_a=0)

        .def(
            "reset", &T::reset,
                "Clear the memory of the local storage buffer")

        .def("__repr__", &T::tostring)
        .def("__len__", &T::length)
        .def("__iter__", &T::iter, py::keep_alive<0, 1>())
        .def("__getitem__", [](T& v, usize n){ return v.getitem(n); })
        .def("__getitem__", [](T& v, py::slice slice){ return v.getitem(slice); })
        .def("__setitem__", &T::setitem)
        .def("__eq__", &T::operator==)
        .def("__ne__", &T::operator!=);

     string const_name = "c_" + string{type_name};
     define_const_variable<T>(m, const_name.c_str());
}


void define_variables(py::module& m)
{   
    define_variable<Ptr>(m, "ptr");
    define_variable_buffer<VariableBuffer>(m, "buf");
//    define_variable_buffer<VariablePtrToBuffer>(m, "p_buf");
    define_variable_buffer<VariableString>(m, "str");
    define_variable_array<PyVariableArray>(m, "arr");

    #define F(type, name) define_variable<type>(m, name);
    FOR_EACH_INT_TYPE(F)
    #undef F

    m.attr("int") = m.attr("i32");
    m.attr("uint") = m.attr("u32");
    m.attr("usize") = m.attr("ptr");
}


void define_instruction(py::module& m)
{
    py::class_<Instruction> inst_class(m, "Instruction");

    py::enum_<Instruction::MachineMode>(inst_class, "Mode")
        .value("Long64", Instruction::MachineMode::LONG_64)
        .value("LongCompat32", Instruction::MachineMode::LONG_COMPAT_32)
        .value("LongCompat16", Instruction::MachineMode::LONG_COMPAT_16)
        .value("Legacy32", Instruction::MachineMode::LEGACY_32)
        .value("Legacy16", Instruction::MachineMode::LEGACY_16)
        .value("Real16", Instruction::MachineMode::REAL_16)
        .export_values();

    py::enum_<Instruction::AddressWidth>(inst_class, "AddressWidth")
        .value("W16", Instruction::AddressWidth::WIDTH_16)
        .value("W32", Instruction::AddressWidth::WIDTH_32)
        .value("W64", Instruction::AddressWidth::WIDTH_64)
        .export_values();

    py::enum_<Instruction::Format>(inst_class, "Format")
        .value("ATT", Instruction::Format::ATT)
        .value("Intel", Instruction::Format::INTEL)
        .value("IntelMasm", Instruction::Format::INTEL_MASM)
        .export_values();

    inst_class
        .def_readonly("length", &Instruction::length,
                        "The length of the instruction in bytes")
    ;

    py::class_<Instruction::Decoder>(m, "InstructionDecoder")
        .def(
            py::init<Instruction::MachineMode, Instruction::AddressWidth>(), 
                "Create an instruction decoder for the given machine"
                "mode"_a, "address_width"_a)
        .def(
            py::init(instruction_decoder_create),
                "Create an instruction decoder for the given architecture"
                "arch"_a)

        .def(
            "set_format", &Instruction::Decoder::set_format,
                "",
                "fmt"_a=Instruction::Format::INTEL)
        
        .def(
            "format", &Instruction::Decoder::format,
                "",
                "instruction"_a, "runtime_address"_a=UINT64_MAX)

        .def(
            "iter", instruction_iter,
                "",
                "data"_a)

        .def(
            "extract_searchable_bytes", instruction_extract_searchable_bytes,
                "",
                "raw_code"_a, "target_instruction_offset"_a, "max_size"_a=UINT64_MAX)           
    ;
}

//endregion


PYBIND11_MODULE(c, m)
{
    #define STRINGIFY(x) #x
    #define MACRO_STRINGIFY(x) STRINGIFY(x)
    #ifdef VERSION_INFO
        m.attr("__version__") = MACRO_STRINGIFY(VERSION_INFO);
    #else
        m.attr("__version__") = "dev";
    #endif

    define_process(m);
    
    define_address(m);

    define_buffer(m);

    define_hack(m);

    define_variables(m);

    define_instruction(m);
}

// pygamehack.c.str Python reference implementation
//
/*

from typing import Union

from pygamehack.c import buf
from ..variable import IBufferContainerVariable, IConstVariable


class String(buf, IBufferContainerVariable):
    """
    String Variable that implements the IContainerVariable Interface
    """
    __slots__ = ()

    def get(self) -> str:
        size = super().get().strlen()
        return super().get().read_string(0, size) if size else ''

    def read(self) -> str: # noqa
        super().read()
        size = super().get().strlen()
        super().get().resize(size)
        return super().get().read_string(0, size) if size else ''

    def write(self, value: str): # noqa
        if len(value) > super().get().size:
            raise RuntimeError(f'str[{len(value)}] too large to fit in buffer[{super().get().size}]')
        super().get().write_string(0, value)

    def __getitem__(self, i: Union[int, slice]):
        if isinstance(i, slice):
            start, stop, step = i.indices(super().get().size)
            assert step == 1, 'Do not support step>1 for string slicing'
            if step == 1:
                return super().get().read_string(start, stop)
            else:
                return super().get().read_string(start, stop)[0:-1:step]
        else:
            self._check_bounds(i)
            return chr(super().get().read_i8(i))

    def __setitem__(self, i: int, value: str):
        assert len(value) == 1
        self._check_bounds(i)
        super().get().write_i8(i, ord(value))

    def __iter__(self):
        for i in range(super().get().strlen()):
            yield chr(super().get().read_i8(i))

    def __len__(self):
        return super().get().strlen()

    def __hash__(self):
        return hash(super().get().read_string())

    def __eq__(self, other):
        if isinstance(other, String):
            return object.__eq__(self, other)
        else:
            return isinstance(other, str) and len(other) == super().get().strlen() and super().get().read_string() == other

    def _check_bounds(self, i):
        assert i < super().get().size, f"String index {i} out of bounds ({super().get().size})"


class CString(IConstVariable, String):
    """
    Const version of String Variable
    """
    __slots__ = ()


*/

// pygamehack.c.arr Python reference implementation
//
/*

import copy
from typing import Any, List, Optional, TypeVar, Tuple, Union

from pygamehack.c import Address, buf
from ..struct_meta import StructMeta, StructType
from ..variable import IBufferContainerVariable, IConstVariable


T = TypeVar('T')


class Array(buf, IBufferContainerVariable):
    """
    Array Variable that implements the IContainerVariable Interface
    """
    __slots__ = ('__value_type', '__values', '__read', '__write')

    @property
    def value_type(self) -> StructType:
        return copy.copy(self.__value_type)

    def get(self) -> 'Array':
        return self

    def read(self, n: int = 0, starting_at: int = 0) -> 'Array':
        super().read(starting_at * self.__value_type.size, n * self.__value_type.size)
        return self

    def write(self, values: List[T], starting_at: int = 0):
        if self.__values is None:
            self._write_buffer(values, starting_at)
        else:
            self._write_values(values, starting_at)

    def flush(self, n: int = 0, starting_at: int = 0):
        super().flush(n * self.__value_type.size, starting_at * self.__value_type.size)

    def reset(self):
        if self.__values is not None:
            self.__values = [_ArrayLazyElement() for _ in range(len(self))]
        super().get().clear()

    @classmethod
    def __class_getitem__(cls, item: Tuple[Any, int]):
        if not isinstance(item, tuple) or StructType.is_compound_type_tuple(item):
            raise RuntimeError('Forgot to provide size in array definition')
        return StructType(item[0], StructType.LAZY_SIZE, item[1], container_type=cls)

    def __init__(self, address: Optional[Address], size: int, **kwargs):
        assert 'type' in kwargs, 'Must provide a value type when initializing an Array'

        self.__value_type = kwargs['type']

        if StructMeta.check_buffer_view_kwargs(address, kwargs):
            super().__init__(kwargs['parent_buffer'], kwargs['offset_in_parent'], size * self.__value_type.size)  # noqa
        else:
            super().__init__(address, size * self.__value_type.size)

        if StructType.is_basic_type(self.value_type):
            self.__values: Optional[List[Any]] = None
            type_name = self.value_type.__name__
            type_size = self.__value_type.size
            read_method = getattr(super().get(), 'read_' + type_name)
            write_method = getattr(super().get(), 'write_' + type_name)
            self.__read = lambda i: read_method(i * type_size)
            self.__write = lambda i, v: write_method(i * type_size, v)
        else:
            self.__values = [_ArrayLazyElement() for _ in range(size)]
            self.__read = None
            self.__write = None

    def __getitem__(self, i: Union[int, slice]) -> T:
        if self.__values is None:
            return self._getitem_buffer(i)
        else:
            return self._getitem_values(i)

    def __setitem__(self, i: int, value: T):
        if self.__values is None:
            self._setitem_buffer(i, value)
        else:
            self._setitem_values(i, value)

    def __iter__(self):
        if self.__values is not None:
            return self.__values.__iter__()
        else:
            return self._iter_buffer()

    def __len__(self):
        return super().get().size / self.__value_type.size

    def __hash__(self):
        return hash(tuple(v for v in self))

    def __eq__(self, other):
        if isinstance(other, Array):
            return object.__eq__(self, other)
        else:
            return isinstance(other, list) \
                   and len(other) == len(self) \
                   and all(v == other[i] for i, v in enumerate(self))

    def _check_bounds(self, i):
        assert i < super().get().size, f"Array index {i} out of bounds ({super().get().size})"

    def _create_element(self, i):
        return self.__value_type(None, buffer=True, parent_buffer=self, offset_in_parent=i * self.__value_type.size)

    def _exists(self, i):
        return not isinstance(self.__values[i], _ArrayLazyElement)

    def _iter_buffer(self, sl: slice = slice(0, -1)):
        start, stop, step = sl.indices(len(self))
        for idx in range(start, stop, step):
            yield self.__read(idx)

    def _getitem_buffer(self, i):
        if isinstance(i, slice):
            return self._iter_buffer(i)
        else:
            return self.__read(i)

    def _setitem_buffer(self, i, value):
        self.__write(i, value)

    def _getitem_values(self, i):
        if isinstance(i, slice):
            return self.__values[i]
        else:
            self._check_bounds(i)

            if not self._exists(i):
                self.__values[i] = self._create_element(i)

            if StructType.is_buffer_subclass(self.__value_type)\
                    or (isinstance(self.__value_type, StructType) and self.__value_type.is_container):
                return self.__values[i].get()
            else:
                return self.__values[i].read()

    def _setitem_values(self, i, value):
        self._check_bounds(i)

        if i >= len(self.__values):
            self.__values.extend(_ArrayLazyElement() for _ in range(i - len(self.__values) + 1))

        if not self._exists(i):
            self.__values[i] = self._create_element(i)

        self.__values[i].write(value)

    def _write_buffer(self, values, starting_at):
        for i, v in enumerate(values):
            self.__write(starting_at + i, v)

    def _write_values(self, values, starting_at):
        for i in range(len(values), starting_at + len(values)):
            self.__values.append(self._create_element(i))

        for i, v in enumerate(values):
            self.__values[starting_at + i].write(v)


class CArray(IConstVariable, Array):
    """
    Const version of Array Variable
    """
    __slots__ = ()


class _ArrayLazyElement(object):
    __slots__ = ()

    def get(self):
        raise RuntimeError('Attempt to access _ArrayLazyElement')

    def read(self):
        raise RuntimeError('Attempt to access _ArrayLazyElement')

    def write(self, v):
        raise RuntimeError('Attempt to access _ArrayLazyElement')

*/
