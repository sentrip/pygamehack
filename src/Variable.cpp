#include "Variable.h"
#include "Address.h"
#include "Process.h"

#include <cassert>

namespace pygamehack {

//region VariableBuffer

VariableBuffer::Variable(Address& address, usize size):
    value{address.process(), size},
    _address{&address}
{}

Buffer& VariableBuffer::get()
{
    return value;
}

Buffer& VariableBuffer::read(uptr offset, uptr size)
{
    variable_read(*_address, offset, value.data() + offset, clamped_size(offset, size, value.size()));
    return value;
}

void VariableBuffer::write(const Buffer& v, uptr offset)
{
    value.write_buffer(offset, v);
}

void VariableBuffer::flush(uptr offset, uptr size) const
{
    variable_write(*_address, offset, value.data() + offset, clamped_size(offset, size, value.size()));
}

const Address& VariableBuffer::address() const
{
    return *_address;
}

void VariableBuffer::reset()
{
    value.clear();
}

//endregion

//region VariablePtrToBuffer

VariablePtrToBuffer::Variable(Address& address, usize size):
    value{address.process(), size},
    _address{&address}
{}

Buffer& VariablePtrToBuffer::get()
{
    return value;
}

Buffer& VariablePtrToBuffer::read(uptr offset, uptr size)
{
    PGH_ASSERT(_address->loaded(), "Attempting to read a variable from an address that is not loaded");
    uptr real_address{};
    _address->process().read_memory(&real_address, _address->value(), _address->process().get_ptr_size());
    _address->process().read_memory(value.data() + offset, real_address + offset, VariableBuffer::clamped_size(offset, size, value.size()));
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
    _address->process().read_memory(&real_address, _address->value(), _address->process().get_ptr_size());
    _address->process().write_memory(real_address + offset, value.data() + offset, VariableBuffer::clamped_size(offset, size, value.size()));
}

const Address& VariablePtrToBuffer::address() const
{
    return *_address;
}

void VariablePtrToBuffer::reset()
{
    value.clear();
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

void VariableBuffer::variable_read(Address& address, uptr offset, u8* value, usize value_size)
{
    PGH_ASSERT(address.loaded(), "Attempting to read a variable from an address that is not loaded");
    address.process().read_memory(value, address.value() + offset, value_size ? value_size : address.process().get_ptr_size());
}

void VariableBuffer::variable_write(Address& address, uptr offset, const u8* value, usize value_size)
{
    PGH_ASSERT(address.loaded(), "Attempting to write a variable to an address that is not loaded");
    address.process().write_memory(address.value() + offset, value, value_size ? value_size : address.process().get_ptr_size());
}

//endregion

}
