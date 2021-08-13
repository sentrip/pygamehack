#include "Variable.h"
#include "Address.h"
#include "Process.h"

#include <cassert>

namespace pygamehack {

//region VariableBufferBase

VariableBufferBase::VariableBufferBase(Address& address, usize size):
    value{address.process(), size},
    _address{&address},
    _parent{nullptr},
    _offset_in_parent{}
{}

VariableBufferBase::VariableBufferBase(VariableBufferBase& parent, uptr offset, usize size):
    value{parent.value, offset, size},
    _address{parent._address},
    _parent{&parent},
    _offset_in_parent{offset}
{}

Buffer& VariableBufferBase::get()
{
    return value;
}

Buffer& VariableBufferBase::read(uptr size, uptr offset)
{
    uptr real_offset = offset + offset_in_parent();
    variable_read(address(), real_offset, value.data() + offset, clamped_size(offset, size, value.size()));
    return value;
}

void VariableBufferBase::write(const u8* data, usize size, uptr offset)
{
    PGH_ASSERT(size <= (value.size() - offset), "Data too large to fit into buffer");
    memcpy(value.data() + offset, data, size);
}

void VariableBufferBase::flush(uptr size, uptr offset) const
{
    uptr real_offset = offset + offset_in_parent();
    usize real_size = clamped_size(offset, size, value.size());
    variable_write(address(), real_offset, value.data() + offset, real_size);
}

const Address& VariableBufferBase::address() const
{
    return *_address;
}

void VariableBufferBase::reset()
{
    value.clear();
}

bool VariableBufferBase::is_view() const
{
    return _parent != nullptr;
}

uptr VariableBufferBase::offset_in_parent() const
{
    return _offset_in_parent;
}

VariableBufferBase& VariableBufferBase::parent()
{
    PGH_ASSERT(is_view(), "Can only access the parent of buffer-view variables");
    return *_parent;
}

std::string_view VariableBufferBase::get_view() const
{
    return std::string_view{(const char*)value.data(), value.size()};
}

usize VariableBufferBase::clamped_size(uptr offset, usize size, usize buffer_size)
{
    PGH_ASSERT(offset < buffer_size, "Offset out of range of buffer");
    return size ? std::min<usize>(size, buffer_size - offset) : (buffer_size - offset);
}

void VariableBufferBase::variable_read(const Address& address, uptr offset, u8* value, usize value_size)
{
    PGH_ASSERT(address.loaded(), "Attempting to read a variable from an address that is not loaded");
    address.process().read_memory(value, address.value() + offset, value_size ? value_size : address.process().get_ptr_size());
}

void VariableBufferBase::variable_write(const Address& address, uptr offset, const u8* value, usize value_size)
{
    PGH_ASSERT(address.loaded(), "Attempting to write a variable to an address that is not loaded");
    address.process().write_memory(address.value() + offset, value, value_size ? value_size : address.process().get_ptr_size());
}

//endregion

//region VariableBuffer

void VariableBuffer::write(const Buffer& v, uptr offset)
{
    value.write_buffer(offset, v);
}

//endregion

//region VariableString

string VariableString::get() const
{
    return string((const char*)value.data());
}

string VariableString::read(uptr size, uptr offset)
{
    uptr real_offset = offset + offset_in_parent();
    usize real_size = size ? size : address().process().find_char(0, address().value() + real_offset, 4096);
    if (real_size >= value.size()) value.resize(real_size);
    VariableBufferBase::read(real_size, offset);
    return string{(const char*)(value.data() + offset), real_size};
}

void VariableString::write(const string& v, uptr offset)
{
    PGH_ASSERT(v.size() <= (value.size() - offset), "String too large to fit into buffer");
    VariableBufferBase::write((const u8*)v.c_str(), v.size(), offset);
}

usize VariableString::size() const
{
    return value.size();
}

usize VariableString::strlen() const
{
    return strnlen_s((const char*)value.data(), value.size() + 1);
}

string VariableString::slice(i64 begin, i64 end, i64 step)
{
    if (step == 1) {
        return string{(const char*)(value.data() + begin), (const char*)(value.data() + end)};
    }
    else {
        string v{};
        v.reserve(((end - begin) / std::abs(step)) + 1);
        for (i64 i = begin; i != end; i += step) {
            v.append((const char*)(value.data() + i), 1);
        }
        return v;
    }
}

//endregion

//region VariablePtrToBuffer

//Buffer& VariablePtrToBuffer::read(uptr size, uptr offset)
//{
//    PGH_ASSERT(_address->loaded(), "Attempting to read a variable from an address that is not loaded");
//    uptr real_address{};
//    uptr real_offset = offset + offset_in_parent();
//    const auto& addr = address();
//    addr.process().read_memory(&real_address, addr.value() + real_offset, addr.process().get_ptr_size());
//    addr.process().read_memory(value.data() + offset, real_address, VariableBufferBase::clamped_size(offset, size, value.size()));
//    return value;
//}
//
//void VariablePtrToBuffer::write(const Buffer& v, uptr offset)
//{
//    value.write_buffer(offset, v);
//}
//
//void VariablePtrToBuffer::flush(uptr size, uptr offset) const
//{
//    PGH_ASSERT(_address->loaded(), "Attempting to write a variable to an address that is not loaded");
//    uptr real_address{};
//    uptr real_offset = offset + offset_in_parent();
//    const auto& addr = address();
//    addr.process().read_memory(&real_address, addr.value() + real_offset, addr.process().get_ptr_size());
//    addr.process().write_memory(real_address, value.data() + offset, VariableBufferBase::clamped_size(offset, size, value.size()));
//}

//endregion

}
