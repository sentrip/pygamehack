#ifndef PYWRAPPERS_H
#define PYWRAPPERS_H

#include <pybind11/pybind11.h>
#include <pybind11/operators.h>
#include <pybind11/stl.h>

#include "../Hack.h"
#include "../Buffer.h"
#include "../Address.h"
#include "../Variable.h"
#include "../Instruction.h"

namespace py = pybind11;

namespace pygamehack {

//region Helpers

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
        }, py::arg("memo"));
}

//endregion

//region Python wrappers - Process

static constexpr auto process_iter = [](py::object& callback)
{
    Process::iter([&callback](const ProcessInfo& info){
        return py::cast<bool>(callback(info));
    });
};

static constexpr auto process_follow = [](Process& self, uptr begin, const uptr_path& offsets)
{
    py::gil_scoped_release release;
    return self.follow(begin, offsets);
};

static constexpr auto process_iter_regions = [](Process& self, uptr begin, usize size, py::object& callback, Memory::Protect prot, usize block_size)
{
    py::gil_scoped_release release;
    self.iter_regions(begin, size, [&self, &callback](uptr rbegin, usize rsize, Memory::Protect protect, const u8* data) {
        Buffer buffer{ self, (u8*)data, rsize };
        py::gil_scoped_acquire  acquire_gil;
        return py::cast<bool>(callback(rbegin, protect, buffer));
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

static constexpr auto buffer_read_dynamic_string = [](Buffer& self, uptr offset, usize size)
{
    return buffer_read_string(self, offset, size ? std::min<usize>(size, self.size() - offset) : std::min<usize>(self.strlen(offset), self.size() - offset));
};

static constexpr auto buffer_write_string = [](Buffer& self, uptr offset, const string& data)
{
    py::gil_scoped_release release;
    return self.write_string(offset, data);
};

//endregion

//region Python wrappers - Hack

static constexpr auto hack_find = [](Hack& self, i64 value, uptr begin, usize size)
{
    py::gil_scoped_release release;
    return self.find(i8(value), begin, size);
};

static constexpr auto hack_scan = [](Hack& self, Hack::Scan& scan)
{
    py::gil_scoped_release release;
    return self.scan(scan);
};

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

static constexpr auto hack_read_dynamic_string = [](Hack& self, uptr src, usize size, usize max_len)
{
    return hack_read_string(self, src, size ? size : self.find(0, src, max_len));
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

static constexpr auto hack_scan_modify = [](Hack& self, Hack::Scan& scan, py::object& callback)
{
    py::gil_scoped_release release;
    return self.scan_modify(scan, [&callback](Hack::Scan& s) {
        py::gil_scoped_acquire acquire_gil;
        return py::cast<bool>(callback(s));
    });
};

static constexpr auto hack_scan_set_value = [](Hack::Scan& self, py::object& value)
{
    if (py::isinstance(value, py::globals()["str"])) {
        self.set_value(value.cast<string>());
    }
    else {
        u8 buffer[8]{};

        if (py::isinstance(value, py::globals()["int"])) {
            PGH_ASSERT(self.value_size <= 8, "Cannot set non-int value with a int");
            auto v = value.cast<i64>();
            memcpy(buffer, &v, self.value_size);
        }
        else if (py::isinstance(value, py::globals()["float"])) {
            PGH_ASSERT(self.value_size <= 8, "Cannot set non-float value with a float");
            auto v = value.cast<double>();
            memcpy(buffer, &v, self.value_size);
        }
        else if (py::isinstance(value, py::globals()["bool"])) {
            PGH_ASSERT(self.value_size == 1, "Cannot set non-bool value with a bool");
            auto v = value.cast<bool>();
            memcpy(buffer, &v, self.value_size);
        }
        else {
            PGH_ASSERT(false, "Unrecognized type encountered when setting memory scan value");
        }

        self.set_value(self.type_id(), buffer, self.value_size);
    }
};

//endregion

//region Python wrappers - Instruction

static constexpr auto instruction_decoder_create = [](Process::Arch arch)
{
    return Instruction::Decoder(
        arch == Process::Arch::X64 ? Instruction::MachineMode::LONG_64 : Instruction::MachineMode::LEGACY_32,
        arch == Process::Arch::X64 ? Instruction::AddressWidth::WIDTH_64 : Instruction::AddressWidth::WIDTH_32);
};

static constexpr auto instruction_iter = [](const Instruction::Decoder& decoder, const string& data)
{
    return py::make_iterator(
        Instruction::Iterator(&decoder, (const u8*)data.c_str(), data.size()),
        Instruction::Iterator(&decoder)
    );
};

static constexpr auto instruction_extract_searchable_bytes = [](const Instruction::Decoder& decoder, const string& raw_code, uptr target_instruction_offset, usize max_size)
{
    auto [code, offset, size] = decoder.extract_searchable_bytes(raw_code, target_instruction_offset, max_size);
    return py::make_tuple(py::bytes(code), offset, size);
};

//endregion

}

#endif
