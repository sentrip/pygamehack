#include "Buffer.h"
#include "Process.h"
#include "Hack.h"

#include <cassert>

namespace pygamehack {


Buffer::Buffer(Hack& hack, usize size):
    Buffer{hack.process(), size}
{}
    
Buffer::Buffer(const Process& process, usize size):
    process{&process},
    _is_small{size <= SMALL_SIZE},
    _owns_memory{true},
    _size{size}
{
    PGH_ASSERT(size, "Cannot create buffer with size=0");
    if (!_is_small) { _data = (u8*)malloc(size); }
    memset(data(), 0, size);
}

Buffer::Buffer(const Process& process, u8* data, usize size):
    process{&process},
    _is_small{false},
    _owns_memory{false},
    _size{size},
    _data{data}
{
    PGH_ASSERT(size, "Cannot create buffer with size=0");
}

Buffer::Buffer(Buffer& src, uptr offset, usize size):
    process{src.process},
    _is_small{false},
    _owns_memory{false},
    _size{size},
    _data{src.data() + offset}
{
    PGH_ASSERT(size, "Cannot create buffer with size=0");
    PGH_ASSERT(size <= src._size - offset, "Cannot create buffer view that overflows its parent");
}

Buffer::Buffer(const Buffer& v):	
    process{v.process},
    _is_small{v._is_small},
    _owns_memory{ true },
    _size{ v._size }
{
    if (!_is_small) { _data = (u8*)malloc(v._size); }
	memcpy(data(), v.data(), v._size);
}

Buffer& Buffer::operator=(const Buffer& v)
{
    if (&v != this) {
        PGH_ASSERT(v._owns_memory, "Cannot copy from a buffer view");
        process = v.process;
        _owns_memory = true;
        resize(v._size);
	    memcpy(data(), v.data(), _size);
    }
	return *this;
}

Buffer::Buffer(Buffer&& v) noexcept
{
    process = v.process;
    _is_small = v._is_small;
    _owns_memory = v._owns_memory;
    _size = v._size;
    if (v._is_small) {
        memcpy(storage, v.storage, _size);
    }
    else {
        _data = v._data;
        v._owns_memory = false;
    }
}

Buffer& Buffer::operator=(Buffer&& v) noexcept
{
	if (&v != this) {
        process = v.process;
        if (v._is_small) {
            memcpy(storage, v.storage, v._size);
        }
        else {
            if (_owns_memory && !_is_small && _data) free(_data);
            _data = v._data;
            v._owns_memory = false;
        }
        _is_small = v._is_small;
        _owns_memory = v._owns_memory;
        _size = v._size;
    }
	return *this;
}

Buffer::~Buffer()
{
    if (_owns_memory && !_is_small && _data) free(data());
}

u8* Buffer::data()
{
    return _is_small ? storage : _data;
}

const u8* Buffer::data() const
{
    return _is_small ? storage : _data;
}

usize Buffer::size() const
{
    return _size;
}

void Buffer::clear()
{
    memset(data(), 0, _size);
}

void Buffer::resize(usize size)
{
    if (size == _size) return;

    if (_is_small && size > SMALL_SIZE) {
        grow(size);
    }
    else if (!_is_small && size <= SMALL_SIZE) {
        shrink();
    }
    else if (!_is_small && size > SMALL_SIZE) {
        _data = (u8*)realloc(_data, size);
    }
    _size = size;
}

void Buffer::read_from(uptr src, usize size, uptr offset)
{
    const usize real_size = size ? size : _size;
    PGH_ASSERT(real_size <= (_size - offset), "Read will overflow buffer");
    process->read_memory(data() + offset, src, real_size);
}

void Buffer::write_to(uptr dst, usize size, uptr offset) const
{
    const usize real_size = size ? size : _size;
    PGH_ASSERT((offset + real_size) <= _size, "Write will overflow buffer");
    process->write_memory(dst, data() + offset, real_size);
}

void Buffer::read_buffer(uptr offset, Buffer& dst) const
{
    PGH_ASSERT(offset + dst.size() <= _size, "Read will overflow buffer");
    memcpy(dst.data(), data() + offset, dst._size);
}

void Buffer::write_buffer(uptr offset, const Buffer& src)
{
    PGH_ASSERT((size() - offset) >= src.size(), "Write will overflow buffer");
    memcpy(data() + offset, src.data(), src._size);
}

uptr Buffer::read_ptr(uptr offset) const
{
    uptr v{};
    PGH_ASSERT((offset + process->get_ptr_size()) <= _size, "Read will overflow buffer");
    memcpy(&v, data() + offset, process->get_ptr_size());
    return v;
}

void Buffer::write_ptr(uptr offset, uptr v)
{
    PGH_ASSERT((offset + process->get_ptr_size()) <= _size, "Write will overflow buffer");
    memcpy(data() + offset, &v, process->get_ptr_size());
}

string Buffer::read_string(uptr offset, usize size) const
{
    const usize real_size = size ? size : _size;
    PGH_ASSERT(offset + real_size <= _size, "Read will overflow buffer");
    return string{(const char*)data() + offset, real_size};
}

void Buffer::write_string(uptr offset, const string& v)
{
	PGH_ASSERT((_size - offset) >= v.size(), "Write will overflow buffer");
    memcpy(data() + offset, v.c_str(), v.size());
}

usize Buffer::strlen(uptr offset) const
{
    PGH_ASSERT(offset <= _size, "Offset out of range of Buffer");
    return strnlen_s((const char*)(data() + offset), _size - offset + 1);
}

void Buffer::grow(usize size)
{
    PGH_ASSERT(_owns_memory, "Cannot grow buffer view");
    auto* ptr = (u8*)malloc(size);
    memcpy(ptr, storage, _size);
    _data = ptr;
    _is_small = false;
}

void Buffer::shrink()
{
    PGH_ASSERT(_owns_memory, "Cannot shrink buffer view");
    auto* ptr = _data;
    memcpy(storage, ptr, _size);
    free(ptr);
    _is_small = true;
}

bool Buffer::operator==(const Buffer& other) const
{
    return _is_small == other._is_small && _size == other._size && memcmp(data(), other.data(), _size) == 0;
}

bool Buffer::operator!=(const Buffer& other) const
{
    return !(*this == other);
}

}