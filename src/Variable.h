
#ifndef PYGAMEHACK_VARIABLE_H
#define PYGAMEHACK_VARIABLE_H

#include "Buffer.h"

namespace pygamehack {


struct Ptr{ static constexpr u32 TAG = UINT32_MAX; };
//struct PtrToBuffer{};

using VariableBuffer = Variable<Buffer>;
//using VariablePtrToBuffer = Variable<PtrToBuffer>;
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


class VariableBufferBase {
public:
    VariableBufferBase(Address& address, usize size);
    VariableBufferBase(VariableBufferBase& parent, uptr offset, usize size);

    const Address&  address() const;
    Buffer&         get();

    void            write(const u8* data, usize size, uptr offset = 0);
    Buffer&         read(uptr size = 0, uptr offset = 0);
    void            flush(uptr size = 0, uptr offset = 0) const;
    void            reset();

    bool            is_view() const;
    uptr            offset_in_parent() const;
    VariableBufferBase& parent();

    std::string_view get_view() const;

protected:
    template<typename T>
    friend class Variable;

    static usize clamped_size(uptr offset, usize size, usize buffer_size);
    static void variable_read(const Address& address, uptr offset, u8* value, usize value_size);
    static void variable_write(const Address& address, uptr offset, const u8* value, usize value_size);

    Buffer value;
    Address* _address{};
    VariableBufferBase* _parent{};
    uptr _offset_in_parent{};
};


template<>
class Variable<Buffer>: public VariableBufferBase {
public:
    using VariableBufferBase::VariableBufferBase;

    void            write(const Buffer& v, uptr offset = 0);

private:
    using VariableBufferBase::value;
    using VariableBufferBase::_address;
    using VariableBufferBase::_parent;
};


template<>
class Variable<string> : public VariableBufferBase {
public:
    using VariableBufferBase::VariableBufferBase;

    string          get() const;
    string          read(uptr size = 0, uptr offset = 0);
    void            write(const string& v, uptr offset = 0);

    usize           size() const;
    usize           strlen() const;
    string          slice(i64 begin, i64 end, i64 step);

private:
    using VariableBufferBase::value;
    using VariableBufferBase::_address;
    using VariableBufferBase::_parent;
};


//template<>
//class Variable<PtrToBuffer>: public VariableBufferBase {
//public:
//    using VariableBufferBase::VariableBufferBase;
//
//    Buffer&         read(uptr size = 0, uptr offset = 0);
//    void            write(const Buffer& v, uptr offset = 0);
//    void            flush(uptr size = 0, uptr offset = 0) const;
//
//private:
//    using VariableBufferBase::value;
//    using VariableBufferBase::_address;
//    using VariableBufferBase::_parent;
//};


//region Template Implementation

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
    if constexpr(std::is_same_v<RT, Ptr>) {
        VariableBufferBase::variable_read(*_address, 0, (u8*)&value, 0);
    }
    else {
        VariableBufferBase::variable_read(*_address, 0, (u8*)&value, sizeof(T));
    }
    return value;
}

template<typename RT>
void Variable<RT>::write(const T& v)
{
    value = v;
    if constexpr(std::is_same_v<RT, Ptr>) {
        VariableBufferBase::variable_write(*_address, 0, (const u8*)&value, 0);
    }
    else {
        VariableBufferBase::variable_write(*_address, 0, (const u8*)&value, sizeof(T));
    }
}

template<typename RT>
void Variable<RT>::reset()
{
    value = {};
}

//endregion

}

#endif
