
#ifndef PYGAMEHACK_VARIABLE_H
#define PYGAMEHACK_VARIABLE_H

#include "Buffer.h"

namespace pygamehack {


struct Ptr{ static constexpr u32 TAG = UINT32_MAX; };
struct PtrToBuffer{};

using VariableBuffer = Variable<Buffer>;
using VariablePtrToBuffer = Variable<PtrToBuffer>;
using VariableString = Variable<string>;



template<typename RT>
class Variable {
public:
    using T = std::conditional_t<std::is_same_v<RT, Ptr>, uptr, RT>;

    explicit Variable(Address& address);

    const Address&  address() const;
    const T&        get() const;
    const T&        read();
    void            write(const T& v);
    void            reset();

private:
    T value;
    Address* _address{};
};



template<>
class Variable<Buffer> {
public:
    Variable(Address& address, usize size);
    Variable(VariableBuffer& parent, uptr offset, usize size);

    const Address&  address() const;
    Buffer&         get();
    Buffer&         read(uptr offset = 0, uptr size = 0);
    void            write(const Buffer& v, uptr offset = 0);
    void            flush(uptr offset = 0, uptr size = 0) const;
    void            reset();

    bool            is_view() const;
    uptr            offset_in_parent() const;
    VariableBuffer& parent();

private:
    template<typename T>
    friend class Variable;

    static usize clamped_size(uptr offset, usize size, usize buffer_size);
    static uptr get_offset(const Buffer& parent, const Buffer& child);
    static void variable_read(const Address& address, uptr offset, u8* value, usize value_size);
    static void variable_write(const Address& address, uptr offset, const u8* value, usize value_size);

    Buffer value;
    union {
        Address* _address{};
        VariableBuffer* _parent;
    };
    bool _is_view{};
};



template<>
class Variable<PtrToBuffer> {
public:
    Variable(Address& address, usize size);
    Variable(VariablePtrToBuffer& parent, uptr offset, usize size);

    const Address&  address() const;
    Buffer&         get();
    Buffer&         read(uptr offset = 0, uptr size = 0);
    void            write(const Buffer& v, uptr offset = 0);
    void            flush(uptr offset = 0, uptr size = 0) const;
    void            reset();

    bool            is_view() const;
    uptr            offset_in_parent() const;
    VariablePtrToBuffer& parent();

private:
    Buffer value;
    union {
        Address* _address{};
        VariablePtrToBuffer* _parent;
    };
    bool _is_view{};
};


template<>
class Variable<string> {
public:
    Variable(Address& address);

    const Address&  address() const;
    const string&   get() const;
    const string&   read();
    void            write(const string& v);
    void            reset();

    usize           size() const;
    void            resize(usize size);

private:
    string value;
    Address* _address{};
};




template<typename RT>
Variable<RT>::Variable(Address& address):
    value{},
    _address{&address}
{}

template<typename RT>
const Address& Variable<RT>::address() const
{
    return *_address;
}

template<typename RT>
const typename Variable<RT>::T& Variable<RT>::get() const
{
    return value;
}

template<typename RT>
const typename Variable<RT>::T& Variable<RT>::read()
{
    /*if constexpr(std::is_same_v<T, string>) {
        VariableBuffer::variable_read(*_address, 0, (u8*)value.data(), value.size());
    }
    else*/ if constexpr(std::is_same_v<RT, Ptr>) {
        VariableBuffer::variable_read(*_address, 0, (u8*)&value, 0);
    }
    else {
        VariableBuffer::variable_read(*_address, 0, (u8*)&value, sizeof(T));
    }
    return value;
}

template<typename RT>
void Variable<RT>::write(const T& v)
{
    value = v;
    /*if constexpr(std::is_same_v<T, string>) {
        VariableBuffer::variable_write(*_address, 0, (const u8*)value.c_str(), value.size());
    }
    else*/ if constexpr(std::is_same_v<RT, Ptr>) {
        VariableBuffer::variable_write(*_address, 0, (const u8*)&value, 0);
    }
    else {
        VariableBuffer::variable_write(*_address, 0, (const u8*)&value, sizeof(T));
    }
}

template<typename RT>
void Variable<RT>::reset()
{
    value = {};
}

}


#endif
