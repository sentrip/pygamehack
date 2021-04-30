#ifndef PYGAMEHACK_BUFFER_H
#define PYGAMEHACK_BUFFER_H

#include "config.h"

namespace pygamehack {


class Buffer {
public:
	// Owns memory
	Buffer(Hack& hack, usize size);
    Buffer(const Process& process, usize size);

	// Does not own memory (src owns memory)
	Buffer(Buffer& src, uptr offset, usize size);
    
	// Does not own memory (C++ only)
	Buffer(const Process& process, u8* data, usize size);

	// Does nothing if doesn't own memory
    ~Buffer();

	// Properties
	u8*			data();
	const u8*   data() const;
	usize		size() const;

    void        clear();
    void        resize(usize size);

    // Read/Write
    void        read_from(uptr src, usize size, uptr offset = 0u);
    void        write_to(uptr dst, usize size, uptr offset = 0u) const;

    void        read_buffer(uptr offset, Buffer& dst) const;
    void        write_buffer(uptr offset, const Buffer& src);

    uptr        read_ptr(uptr offset) const;
    void        write_ptr(uptr offset, uptr v);

	string      read_string(uptr offset = 0u, usize size = 0u) const;
    void        write_string(uptr offset, const string& v);

    template<typename T>
    void        read(uptr offset, T& dst) const;
    template<typename T>
    void        write(uptr offset, const T& v);
    
    template<typename T>
    T           read_value(uptr offset) const;
    template<typename T>
    void        write_value(uptr offset, T v);

    usize       strlen(uptr offset = 0u) const;

	// Copy/Move constructors and operators
public:
	Buffer(const Buffer& v);
	Buffer& operator=(const Buffer& v);

	Buffer(Buffer&& v) noexcept;
	Buffer& operator=(Buffer&& v) noexcept;

    bool        operator==(const Buffer& other) const;
    bool        operator!=(const Buffer& other) const;

private:
    static constexpr usize SMALL_SIZE = 48;

    void grow(usize size);
    void shrink();

    const Process*  process{ nullptr };
    u64             _is_small: 1;
    u64             _owns_memory: 1;
	u64             _size: 62;
	union {
        u8*             _data{ nullptr };
        u8              storage[SMALL_SIZE];
    };
};


//region Template Implementation

template<typename T>
void Buffer::read(uptr offset, T& dst) const
{
    memcpy(&dst, data() + offset, sizeof(T));
}

template<typename T>
void Buffer::write(uptr offset, const T& v)
{
    memcpy(data() + offset, &v, sizeof(T));
}

template<typename T>
T Buffer::read_value(uptr offset) const
{
    T value;
    read<T>(offset, value);
    return value;
}

template<typename T>
void Buffer::write_value(uptr offset, T v)
{
    write<T>(offset, v);
}

//endregion

}

#endif
