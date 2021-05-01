#include "Variable.h"
#include "Address.h"
#include "Process.h"

#include <cassert>

namespace pygamehack {

//region VariableBuffer

VariableBuffer::Variable(Address& address, usize size):
    value{address.process(), size},
    _address{&address},
    _is_view{false}
{}

VariableBuffer::Variable(VariableBuffer& parent, uptr offset, usize size):
    value{parent.value, offset, size},
    _parent{&parent},
    _is_view{true}
{}

Buffer& VariableBuffer::get()
{
    return value;
}

Buffer& VariableBuffer::read(uptr offset, uptr size)
{
    uptr real_offset = offset + _is_view ? get_offset(_parent->value, value) : 0;
    variable_read(address(), real_offset, value.data() + offset, clamped_size(offset, size, value.size()));
    return value;
}

void VariableBuffer::write(const Buffer& v, uptr offset)
{
    uptr real_offset = offset + _is_view ? get_offset(_parent->value, value) : 0;
    value.write_buffer(offset, v);
}

void VariableBuffer::flush(uptr offset, uptr size) const
{
    uptr real_offset = offset + _is_view ? get_offset(_parent->value, value) : 0;
    variable_write(address(), real_offset, value.data() + offset, clamped_size(offset, size, value.size()));
}

const Address& VariableBuffer::address() const
{
    return _is_view ? _parent->address() : *_address;
}

void VariableBuffer::reset()
{
    value.clear();
}

bool VariableBuffer::is_view() const
{
    return _is_view;
}

uptr VariableBuffer::offset_in_parent() const
{
    PGH_ASSERT(_is_view, "Can only access the offset of buffer-view variables");
    return get_offset(_parent->value, value);
}

VariableBuffer& VariableBuffer::parent()
{
    PGH_ASSERT(_is_view, "Can only access the parent of buffer-view variables");
    return *_parent;
}

//endregion

//region VariablePtrToBuffer

VariablePtrToBuffer::Variable(Address& address, usize size):
    value{address.process(), size},
    _address{&address},
    _is_view{false}
{}

VariablePtrToBuffer::Variable(VariablePtrToBuffer& parent, uptr offset, usize size):
    value{parent.value, offset, size},
    _parent{&parent},
    _is_view{true}
{}

Buffer& VariablePtrToBuffer::get()
{
    return value;
}

Buffer& VariablePtrToBuffer::read(uptr offset, uptr size)
{
    PGH_ASSERT(_address->loaded(), "Attempting to read a variable from an address that is not loaded");
    uptr real_address{};
    uptr real_offset = offset + _is_view ? VariableBuffer::get_offset(_parent->value, value) : 0;
    const auto& addr = address();
    addr.process().read_memory(&real_address, addr.value() + real_offset, addr.process().get_ptr_size());
    addr.process().read_memory(value.data() + offset, real_address, VariableBuffer::clamped_size(offset, size, value.size()));
    return value;
}

void VariablePtrToBuffer::write(const Buffer& v, uptr offset)
{
    value.write_buffer(offset, v);
}

void VariablePtrToBuffer::flush(uptr offset, uptr size) const
{
    PGH_ASSERT(_address->loaded(), "Attempting to write a variable to an address that is not loaded");
    uptr real_address{};
    uptr real_offset = offset + _is_view ? VariableBuffer::get_offset(_parent->value, value) : 0;
    const auto& addr = address();
    addr.process().read_memory(&real_address, addr.value() + real_offset, addr.process().get_ptr_size());
    addr.process().write_memory(real_address, value.data() + offset, VariableBuffer::clamped_size(offset, size, value.size()));
}

const Address& VariablePtrToBuffer::address() const
{
    return _is_view ? _parent->address() : *_address;
}

void VariablePtrToBuffer::reset()
{
    value.clear();
}

bool VariablePtrToBuffer::is_view() const
{
    return _is_view;
}

uptr VariablePtrToBuffer::offset_in_parent() const
{
    PGH_ASSERT(_is_view, "Can only offset the parent of buffer-view variables");
    return VariableBuffer::get_offset(_parent->value, value);
}

VariablePtrToBuffer& VariablePtrToBuffer::parent()
{
    PGH_ASSERT(_is_view, "Can only access the parent of buffer-view variables");
    return *_parent;
}

//endregion

//region VariableString

VariableString::Variable(Address& address):
    value{},
    _address{&address}
{}

const Address& VariableString::address() const
{
    return *_address;
}

const string& VariableString::get() const
{
    return value;
}

const string& VariableString::read()
{
    const usize length = _address->process().find_char(0, _address->value(), 4096);
    if (value.size() < length) { value.resize(length); }
    VariableBuffer::variable_read(*_address, 0, (u8*)value.data(), length);
    return value;
}

void VariableString::write(const string& v)
{
    value = v;
    VariableBuffer::variable_write(*_address, 0, (const u8*)value.c_str(), value.size());
}

usize VariableString::size() const
{
    return value.size();
}

void VariableString::resize(usize size)
{
    value.resize(size);
}

void VariableString::reset()
{
    value.clear();
}

//endregion

//region VariableBuffer Private

usize VariableBuffer::clamped_size(uptr offset, usize size, usize buffer_size)
{
    PGH_ASSERT(offset < buffer_size, "Offset out of range of buffer");
    return size ? std::min<usize>(size, buffer_size - offset) : (buffer_size - offset);
}

uptr VariableBuffer::get_offset(const Buffer& parent, const Buffer& child)
{
    PGH_ASSERT(child.data() >= parent.data() && child.data() < parent.data() + parent.size(),
        "Cannot get buffer offset from a buffer that is not a view of another buffer");
    return child.data() - parent.data();
}

void VariableBuffer::variable_read(const Address& address, uptr offset, u8* value, usize value_size)
{
    PGH_ASSERT(address.loaded(), "Attempting to read a variable from an address that is not loaded");
    address.process().read_memory(value, address.value() + offset, value_size ? value_size : address.process().get_ptr_size());
}

void VariableBuffer::variable_write(const Address& address, uptr offset, const u8* value, usize value_size)
{
    PGH_ASSERT(address.loaded(), "Attempting to write a variable to an address that is not loaded");
    address.process().write_memory(address.value() + offset, value, value_size ? value_size : address.process().get_ptr_size());
}

//endregion

}
