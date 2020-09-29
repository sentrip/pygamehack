#include <type_traits>
#include <string>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Hack.h"
#include "libdasm.h"

INSTRUCTION _get_instruction(std::string code, Mode m = Mode::MODE_32)
{
    INSTRUCTION inst{};
    get_instruction(&inst, (unsigned char*)code.data(), m);
    return inst;
}

std::string _get_instruction_string(INSTRUCTION& instruction, Format fmt)
{
    std::string inst_str;
    inst_str.resize(512);
    get_instruction_string(&instruction, fmt, 0, inst_str.data(), inst_str.size());
    inst_str.resize(strnlen_s(inst_str.c_str(), 512));
    return inst_str;
}


std::string get_instruction_string_from_bytes(std::string code, Format fmt, Mode m = Mode::MODE_32)
{
    std::string instruction;
    instruction.resize(256);
    INSTRUCTION inst;
    get_instruction(&inst, (unsigned char*)code.data(), static_cast<Mode>(m));
    get_instruction_string(&inst, static_cast<Format>(fmt), 0, instruction.data(), instruction.size());
    return instruction;
}


namespace py = pybind11;

template<typename T, typename R, typename... Args>
constexpr auto no_gil(R(T::* method)(Args...) const)
{

    if constexpr (std::is_void_v<R>) {
        return [method](const T& self, Args... args) -> void {
            py::gil_scoped_acquire release;
            (self.*method)(args...);
            py::gil_scoped_acquire acquire;
        };
    }  
    else {
        return [method](const T& self, Args... args) -> R {
            py::gil_scoped_acquire release;
            auto result = (self.*method)(args...);
            py::gil_scoped_acquire acquire;
            return result;
        };
    }
}

template<typename T>
void define_buffer_read_write(py::class_<Buffer>& cls, const std::string& type_name)
{
    std::string read_method{ "read_" + type_name };
    std::string read_method_ptr{ read_method + "_ptr" };
    std::string write_method{ "write_" + type_name };
    std::string write_method_ptr{ write_method + "_ptr" };
    std::string read_method_doc{ "Read a " + type_name + " from offset" };
    std::string read_method_ptr_doc{ "Read a " + type_name + " from the pointer found at offset" };
    std::string write_method_doc{ "Write a " + type_name + " to buffer at offset" };
    std::string write_method_ptr_doc{ "Write a " + type_name + " to the pointer found in the buffer at offset" };

    using namespace py::literals;
    cls
        .def(read_method.c_str(), &Buffer::read_basic<T>, read_method_doc.c_str(), "offset"_a)
        .def(read_method_ptr.c_str(), &Buffer::read_ptr_basic<T>, read_method_ptr_doc.c_str(), "offset"_a)
        .def(write_method.c_str(), &Buffer::write_basic<T>, write_method_doc.c_str(), "offset"_a, "value"_a)
        .def(write_method_ptr.c_str(), &Buffer::write_ptr_basic<T>, write_method_ptr_doc.c_str(), "offset"_a, "value"_a);
}

template<typename T, bool define_scan = true>
void define_hack_read_write_scan(py::class_<Hack>& cls, const std::string& type_name)
{
    std::string read_method{ "read_" + type_name };
    std::string write_method{ "write_" + type_name };
    std::string read_method_doc{ "Read a " + type_name + " from address" };
    std::string write_method_doc{ "Write a " + type_name + " to address" };
    std::string scan_doc = type_name;  // TODO: Scan doc

    using namespace py::literals;
    cls
        .def(read_method.c_str(), &Hack::read_memory_basic<T>, read_method_doc.c_str(), "address"_a)
        .def(write_method.c_str(), &Hack::write_memory_basic<T>, write_method_doc.c_str(), "address"_a, "value"_a);
        
    if constexpr (define_scan) {
        cls.def("scan", py::overload_cast<T, Ptr, size_t, size_t>(&Hack::scan<T>, py::const_),
            scan_doc.c_str(), "value"_a, "begin"_a, "size"_a, "n_results"_a=0);
    }
}


template<typename T>
void define_variable(py::module& m, const char* name)
{
    using Var = Variable<T>;
    
    std::string type_name{ name };
    std::string init_doc{ "Create a variable of type " + type_name + " from the given address" };
    std::string init_buffer_doc{ "Create a buffer variable of type " + type_name + " from the given address and size" };
    std::string init_buffer_view_doc{ "Create a buffer view of type " + type_name + " from the given buffer, offset and size" };
    std::string write_doc{ "Write a " + type_name + " to this variable and then write this variable's value to 'address'" };
    
    auto var_class = py::class_<Var>(m, name);

    using namespace py::literals;
    var_class.attr("size") = sizeof(T);

    var_class
        .def_readwrite("address", &Var::address,
            "Address that this variable reads from")
        .def("write", &Var::write,
            write_doc.c_str(), "value"_a);

    if constexpr (std::is_same_v<T, Buffer>) {
        var_class
            .def(py::init<Address&, size_t>(), init_buffer_doc.c_str(), 
                "address"_a, "size"_a)
            .def(py::init<Buffer&, Ptr, size_t>(), init_buffer_view_doc.c_str(), 
                "src"_a, "offset"_a, "size"_a)
            .def("write_contents", &Var::write_direct,
                "Write the contents of the buffer to 'address'");
    }
    else {
        var_class.def(py::init<Address&>(), init_doc.c_str(), "address"_a);
    }

    if constexpr (std::is_trivially_constructible_v<T> && !std::is_same_v<T, Buffer>) {
        var_class
            .def("get", &Var::get,
                "Get the value of this variable without reading memory")
            .def("read", &Var::read,
                "Read the value from memory into this variable and return it");
    }
    else {
        var_class
            .def("get", &Var::get, py::return_value_policy::reference,
                "Get the value of this variable without reading memory")
            .def("read", &Var::read, py::return_value_policy::reference,
                "Read the value from memory into this variable and return it");
    }
}


PYBIND11_MODULE(pygamehack, m)
{
    using namespace py::literals;
    m.attr("__version__") = "1.0";

    // Address
    {
        auto address_class = py::class_<Address>(m, "Address");
        address_class
            .def_property_readonly("type", &Address::get_type,
                "Type of the address (STATIC, DYNAMIC)")
            .def_property_readonly("name", &Address::get_name,
                "Name given to the address")
            .def_property_readonly("module_name", &Address::get_module_name,
                "Name of the module in which the address is found (only for STATIC)")
            .def_property_readonly("address", &Address::get_address,
                "Memory address (int) of this address")
            .def_property_readonly("loaded", &Address::get_is_loaded,
                "True if the address has been loaded from memory")
            
            .def_property_readonly("module_base_address", &Address::get_module_base_address,
                "Base memory address (int) of the module in which the address is found (only for STATIC)")
            .def_property_readonly("static_offset", &Address::get_static_offset,
                "Offset (int) of this address from 'module_base_address' (only for STATIC)")
            .def_property_readonly("hack", &Address::get_hack, py::return_value_policy::reference,
                "Hack to which this address belongs")
            .def_property_readonly("previous", &Address::get_previous, py::return_value_policy::reference,
                "Address that is depended on by this address (only for DYNAMIC, and always loaded before the current address)")
            .def_property_readonly("offsets", &Address::get_offsets,
                "List of offsets to follow when loading this address (only for DYNAMIC, the start of the path is the final address of 'previous' after it is loaded)")
            .def_readwrite("dynamic_offset", &Address::dynamic_offset,
                "Offset (int) of this address from 'address' (only for DYNAMIC, use this when you want to make one more jump without reading the pointer)")
            .def_readwrite("previous_holds_ptr", &Address::previous_holds_ptr,
                "If true then address of 'previous' is read to get the start of this address' path, otherwise it is used as-is without reading and the first offset is simply added to it")
            
            .def("add_backup", py::overload_cast<Address&, const PtrPath&>(&Address::add_backup),
                "")
            .def("add_backup", py::overload_cast<const std::string&, const PtrPath&>(&Address::add_backup),
                "")
            .def("backups", [](Address& self) { return py::make_iterator(self.backups.begin(), self.backups.end()); },
                "")

            .def("valid", &Address::is_valid,
                "True if the address points to valid memory within the process")
            .def("load", &Address::load,
                "Load the address from previous addresses or from memory")
            .def("add_offsets", &Address::add_offsets,
                "Add a list of offsets to the end of the offset path", "offsets"_a)
            .def("pop_offsets", &Address::pop_offsets,
                "Pop n offsets from the end of the offset path", "n"_a);

        // Address enum
        py::enum_<Address::Type>(address_class, "Type")
            .value("STATIC", Address::STATIC)
            .value("DYNAMIC", Address::DYNAMIC)
            .value("MANUAL", Address::MANUAL)
            .export_values();

        // Address flags enum
        enum AddressFlags{};
        py::enum_<AddressFlags>(address_class, "Flags", py::arithmetic())
            .value("NONE", static_cast<AddressFlags>(0))
            .value("ALL", static_cast<AddressFlags>(UINT16_MAX))
            .value("F1", static_cast<AddressFlags>(1 << 0))
            .value("F2", static_cast<AddressFlags>(1 << 1))
            .value("F3", static_cast<AddressFlags>(1 << 2))
            .value("F4", static_cast<AddressFlags>(1 << 3))
            .value("F5", static_cast<AddressFlags>(1 << 4))
            .value("F6", static_cast<AddressFlags>(1 << 5))
            .value("F7", static_cast<AddressFlags>(1 << 6))
            .value("F8", static_cast<AddressFlags>(1 << 7))
            .value("F9", static_cast<AddressFlags>(1 << 8))
            .value("F10", static_cast<AddressFlags>(1 << 9))
            .value("F11", static_cast<AddressFlags>(1 << 10))
            .value("F12", static_cast<AddressFlags>(1 << 11))
            .value("F13", static_cast<AddressFlags>(1 << 12))
            .value("F14", static_cast<AddressFlags>(1 << 13))
            .value("F15", static_cast<AddressFlags>(1 << 14))
            .value("F16", static_cast<AddressFlags>(1 << 15))
            .export_values();
    }

    // Buffer
    {
        auto& buffer_class = py::class_<Buffer>(m, "Buffer")
            .def(py::init<size_t>(),
                "Create a buffer of a given size", "size"_a)

            .def(py::init<Buffer&, Ptr, size_t>(),
                "Create a view into another buffer of the given size starting at the given offset",
                "src"_a, "offset"_a, "size"_a)

            .def_readwrite("hack", &Buffer::hack, py::return_value_policy::reference,
                "The hack that owns this buffer (this is needed to read/write slices and values from pointers in a buffer)")

            .def_property_readonly("size", &Buffer::size,
                "Size of the buffer in bytes")

            .def("clear", &Buffer::clear, py::return_value_policy::reference,
                "Set all bytes in the buffer to 0")
            .def("resize", &Buffer::resize, py::return_value_policy::reference,
                "Change the size of the buffer. If new_size > size, 0s are appended, if new_size < size, the difference is truncated.",
                "new_size"_a)

            .def("read_slice", &Buffer::read_slice, py::return_value_policy::reference,
                "Read a slice of memory of given size from given pointer into the buffer at given offset",
                "ptr"_a, "offset"_a, "size"_a)
            .def("write_slice", &Buffer::write_slice, py::return_value_policy::reference,
                "Write a slice of memory of given size from the buffer to the given pointer",
                "ptr"_a, "offset"_a, "size"_a)

            .def("read_ptr_to_buffer", &Buffer::read_buffer_ptr, py::return_value_policy::reference,
                "Reads the data from a location pointed at by a pointer inside this buffer at the given offset into the given buffer. "
                "The number of bytes read is the size of the given buffer.",
                "offset"_a, "buffer"_a)
            .def("write_ptr_to_buffer", &Buffer::write_buffer_ptr, py::return_value_policy::reference,
                "Writes the data from the given buffer into the location pointed at by a pointer inside this buffer at the given offset. "
                "The number of bytes written is the size of the given buffer.",
                "offset"_a, "buffer"_a)

            .def("read_string", &Buffer::read_string,
                "Read the contents of the buffer as a string")
            .def("write_string", &Buffer::write_string,
                "Write the contents of the given string into the buffer. If the buffer is too small, the string is truncated.",
                "value"_a)
            .def("read_bytes", [](py::handle self) { return py::bytes(py::cast<Buffer&>(self).read_string()); },
                "Read the contents of the buffer as a byte-string")
            .def("write_bytes", &Buffer::write_string, /* implicit bytes conversion */
                "Write the contents of the given byte-string into the buffer. If the buffer is too small, the string is truncated.",
                "value"_a);

        define_buffer_read_write<bool>(buffer_class, "bool");
        define_buffer_read_write<float>(buffer_class, "float");
        define_buffer_read_write<double>(buffer_class, "double");
        define_buffer_read_write<int8_t>(buffer_class, "int8");
        define_buffer_read_write<int16_t>(buffer_class, "int16");
        define_buffer_read_write<int32_t>(buffer_class, "int32");
        define_buffer_read_write<int64_t>(buffer_class, "int64");
        define_buffer_read_write<uint8_t>(buffer_class, "uint8");
        define_buffer_read_write<uint16_t>(buffer_class, "uint16");
        define_buffer_read_write<uint32_t>(buffer_class, "uint32");
        define_buffer_read_write<uint64_t>(buffer_class, "uint64");
        define_buffer_read_write<Ptr>(buffer_class, "ptr");
    }

    // Hack
    {
        auto& hack_class = py::class_<Hack>(m, "Hack")
            .def(py::init<const std::string&>())

            .def_readwrite("process_name", &Hack::process_name, 
                "")
            .def_property_readonly("is_attached", &Hack::is_attached,
                "")
            .def_property_readonly("process_id", &Hack::pid, 
                "")
            .def_property_readonly("ptr_size", &Hack::ptr_size, 
                "")
            .def_property_readonly("max_ptr", &Hack::max_ptr, 
                "")
        
            .def("get_architecture", &Hack::get_architecture, 
                "Process architecture (32-bit or 64-bit) which determines the pointer size in bytes (4 or 8 respectively)")

            .def("get_modules", &Hack::modules, py::return_value_policy::copy, 
                "")
            
            .def("get_module_base_address", &Hack::get_module_base_address,
                "")

            .def("address", &Hack::address, py::return_value_policy::reference)
            .def("add_static_address", &Hack::add_static_address, py::return_value_policy::reference)
            .def("add_dynamic_address", py::overload_cast<const std::string&, Address&, const PtrPath&>(&Hack::add_dynamic_address), py::return_value_policy::reference)
            .def("add_dynamic_address", py::overload_cast<const std::string&, const std::string&, const PtrPath&>(&Hack::add_dynamic_address), py::return_value_policy::reference)
            .def("get_or_add_dynamic_address", &Hack::get_or_add_dynamic_address, py::return_value_policy::reference)
            .def("manual_address", &Hack::manual_address, 
                "Create a manual address that is not part of the loading graph", "address"_a)
            .def("addresses", [](Hack& self) { return py::make_iterator(flatten(self.address_list.begin(), self.address_list.end()), self.address_list.end()); },
                "Iterate over all of the addresses in the hack")

            .def("attach", &Hack::attach)
            .def("load_addresses", &Hack::load_addresses)
            .def("clear_addresses", &Hack::clear_addresses)

            .def("follow_ptr_path", no_gil(&Hack::follow_ptr_path), "", 
                "start"_a, "offsets"_a, "start_is_address_of_ptr"_a = true)
        
            .def("scan_char", no_gil(&Hack::scan_char), "",
                "start"_a, "value"_a, "max_steps"_a = 1000u)
            .def("scan_bytes", no_gil(&Hack::scan<std::string>), "",
                "value"_a, "begin"_a, "size"_a, "n_results"_a=0)

            .def("read_buffer", no_gil(&Hack::read_memory<Buffer>))
            .def("write_buffer", no_gil(&Hack::write_memory<Buffer>))
            .def("read_slice", no_gil(&Hack::read_slice))
            .def("write_slice", no_gil(&Hack::write_slice))
            .def("read_buffer_ptr", no_gil(&Hack::read_buffer_ptr))
            .def("write_buffer_ptr", no_gil(&Hack::write_buffer_ptr))

            .def("read_bytes", [](py::handle self, Ptr ptr, size_t size) {
                py::gil_scoped_release release;
                Buffer buffer{ size };
                py::cast<Hack&>(self).read_memory<Buffer>(ptr, buffer);
                py::bytes bytes(buffer.read_string());
                py::gil_scoped_acquire acquire;
                return bytes;
            })
            .def("write_bytes", [](py::handle self, Ptr ptr, const std::string& bytes) {
                py::gil_scoped_release release;
                Buffer buffer{ bytes.size() };
                buffer.write_string(bytes);
                py::cast<Hack&>(self).write_memory<Buffer>(ptr, buffer);
                py::gil_scoped_acquire acquire;
            })
            .def("iter_regions", [](Hack& self, Ptr begin, size_t size, py::object& callback, size_t block_size){
                self.process.iter_regions(begin, size, [&callback](Ptr rbegin, size_t rsize, uint8_t* data) {
                    Buffer buffer{ data, rsize };
                    return py::cast<bool>(callback(rbegin, buffer));
                }, block_size);
            }, "", "begin"_a, "size"_a, "callback"_a, "block_size"_a=4096);
    
        define_hack_read_write_scan<bool>(hack_class, "bool");
        define_hack_read_write_scan<float>(hack_class, "float");
        define_hack_read_write_scan<double>(hack_class, "double");
        define_hack_read_write_scan<int8_t>(hack_class, "int8");
        define_hack_read_write_scan<int16_t>(hack_class, "int16");
        define_hack_read_write_scan<int32_t>(hack_class, "int32");
        define_hack_read_write_scan<int64_t>(hack_class, "int64");
        define_hack_read_write_scan<uint8_t>(hack_class, "uint8");
        define_hack_read_write_scan<uint16_t>(hack_class, "uint16");
        define_hack_read_write_scan<uint32_t>(hack_class, "uint32");
        define_hack_read_write_scan<uint64_t>(hack_class, "uint64");
        define_hack_read_write_scan<Ptr, false>(hack_class, "ptr");
    }

    // Variables
    define_variable<bool>(m, "bool");
    define_variable<float>(m, "float");
    define_variable<double>(m, "double");
    define_variable<int8_t>(m, "int8");
    define_variable<int16_t>(m, "int16");
    define_variable<int32_t>(m, "int32");
    define_variable<int64_t>(m, "int64");
    define_variable<uint8_t>(m, "uint8");
    define_variable<uint16_t>(m, "uint16");
    define_variable<uint32_t>(m, "uint32");
    define_variable<uint64_t>(m, "uint64");
    // Defining a variable for pointers is not allowed, use uint32/uint64
    define_variable<Buffer>(m, "buffer");

    // Aliases
    m.attr("int") = m.attr("int32");
    m.attr("uint") = m.attr("uint32");

    // Instruction-dissasembly
    {
        py::class_<OPERAND>(m, "Operand")
            .def_readwrite("type", &OPERAND::type, "Operand type (register, memory, etc)")
            .def_readwrite("reg", &OPERAND::reg, "Register (if any)")
            .def_readwrite("basereg", &OPERAND::basereg, "Base register (if any)")
            .def_readwrite("indexreg", &OPERAND::indexreg, "Index register (if any)")
            .def_readwrite("scale", &OPERAND::scale, "Scale (if any)")
            .def_readwrite("dispbytes", &OPERAND::dispbytes, "Displacement bytes (0 = no displacement)")
            .def_readwrite("dispoffset", &OPERAND::dispoffset, "Displacement value offset")
            .def_readwrite("immbytes", &OPERAND::immbytes, "Immediate bytes (0 = no immediate)")
            .def_readwrite("immoffset", &OPERAND::immoffset, "Immediate value offset")
            .def_readwrite("sectionbytes", &OPERAND::sectionbytes, "Section prefix bytes (0 = no section prefix)")
            .def_readwrite("section", &OPERAND::section, "Section prefix value")
            .def_readwrite("displacement", &OPERAND::displacement, "Displacement value")
            .def_readwrite("immediate", &OPERAND::immediate, "Immediate value")
            .def_readwrite("flags", &OPERAND::flags, "Operand flags");

        auto& inst_class = py::class_<INSTRUCTION>(m, "Instruction")
            .def_readwrite("length", &INSTRUCTION::length, "Instruction length")
            //.def_readwrite("type", &INSTRUCTION::type, "Instruction type")
            .def_readwrite("mode", &INSTRUCTION::mode, "Addressing mode")
            .def_readwrite("opcode", &INSTRUCTION::opcode, "Actual opcode")
            .def_readwrite("modrm", &INSTRUCTION::modrm, "MODRM byte")
            .def_readwrite("sib", &INSTRUCTION::sib, "SIB byte")
            .def_readwrite("modrm_offset", &INSTRUCTION::modrm_offset, "MODRM byte offset")
            .def_readwrite("extindex", &INSTRUCTION::extindex, "Extension table index")
            .def_readwrite("fpuindex", &INSTRUCTION::fpuindex, "FPU table index")
            .def_readwrite("dispbytes", &INSTRUCTION::dispbytes, "Displacement bytes (0 = no displacement)")
            .def_readwrite("immbytes", &INSTRUCTION::immbytes, "Immediate bytes (0 = no immediate)")
            .def_readwrite("sectionbytes", &INSTRUCTION::sectionbytes, "Section prefix bytes (0 = no section prefix)")
            .def_readwrite("op1", &INSTRUCTION::op1, "First operand (if any)")
            .def_readwrite("op2", &INSTRUCTION::op2, "Second operand (if any)")
            .def_readwrite("op3", &INSTRUCTION::op3, "Additional operand (if any)")
            .def_readwrite("flags", &INSTRUCTION::flags, "Instruction flags")
            .def_readwrite("eflags_affected", &INSTRUCTION::eflags_affected, "Processor eflags affected")
            .def_readwrite("eflags_used", &INSTRUCTION::eflags_used, "Processor eflags used by this instruction")
            .def_readwrite("iop_written", &INSTRUCTION::iop_written, "Mask of affected implied registers (written)")
            .def_readwrite("iop_read", &INSTRUCTION::iop_read, "Mask of affected implied registers (read)");

        py::enum_<Mode>(inst_class, "Mode")
            .value("M32", Mode::MODE_32)
            .value("M16", Mode::MODE_16)
            .export_values();

        py::enum_<Format>(inst_class, "Format")
            .value("ATT", Format::FORMAT_ATT)
            .value("INTEL", Format::FORMAT_INTEL)
            .export_values();

        m.def("get_instruction", &_get_instruction,
            "Disassemble code from raw bytes into an Instruction object",
            "code"_a, "mode"_a = Mode::MODE_32);

        m.def("get_instruction_string", &_get_instruction_string,
            "Disassemble code from raw bytes into a readable string of instructions",
            "instruction"_a, "format"_a = Format::FORMAT_ATT);
    }
}
