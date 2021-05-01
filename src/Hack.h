
#ifndef PYGAMEHACK_HACK_H
#define PYGAMEHACK_HACK_H

#include "Process.h"
#include "Address.h"

namespace pygamehack {

class Hack {
public:
    Hack();

    // Properties
    const Process&      process() const;

    // Attach/detach
    void                attach(u32 process_id);
    void                attach(const string& process_name);
    void                detach();

	// Memory follow/scan
	uptr                follow(uptr begin, const uptr_path& offsets, bool add_first_offset_to_begin = true) const;

	uptr                find(i8 value, uptr begin, usize size) const;
    
    std::vector<uptr>   scan(const u8* value, usize value_size, uptr begin, usize size, usize max_results, bool regex = false, bool threaded = true) const;

    std::vector<uptr>   scan(const string& value, uptr begin, usize size, usize max_results, bool regex = false, bool threaded = true) const;

	template<typename T>
	std::vector<uptr>   scan(const T& value, uptr begin, usize size, usize max_results, bool threaded = true) const;

    // Address auto-update
    void                start_auto_update(Address& address);
    void                stop_auto_update(Address& address);
    void                set_update_mask(u32 mask = UINT32_MAX);
    void                update();

    // Memory read/write
    void                read_buffer(uptr ptr, Buffer& dst) const;
    void                write_buffer(uptr ptr, const Buffer& src) const;

	uptr                read_ptr(uptr ptr) const;
    void                write_ptr(uptr ptr, uptr v) const;

	string              read_string(uptr ptr, usize size) const;
    void                write_string(uptr ptr, const string& v) const;

	template<typename T>
	void                read(uptr ptr, T& dst) const;

	template<typename T>
	void                write(uptr ptr, const T& src) const;

	template<typename T>
	T                   read_value(uptr ptr) const;

	template<typename T>
	void                write_value(uptr ptr, T src) const;

    // Cheat Engine
public:
    struct CE {
        using Addresses   = std::vector<Address>;
        using AddressPtrs = std::vector<Address*>;
        
        struct Settings {
            u32 max_level = 7;
            u32 max_offset = 4095;
            bool is_compressed = true;
            bool is_aligned = true;
            std::vector<u32> ends_with_offsets{};
        };        

        using PointerScanLoad = std::tuple<Addresses, Settings>;
    };
    
    CE::PointerScanLoad cheat_engine_load_pointer_scan_file(const string& path, bool threaded = true);
    void                cheat_engine_save_pointer_scan_file(const string& path, const CE::AddressPtrs& addresses, const CE::Settings& settings = {}, bool single_file = true);

    // C++ only
public:
    AddressNames&       address_names() { return _address_names; }
    const AddressNames& address_names() const { return _address_names; }

private:    
    using AddressHandleMap = std::unordered_map<Address*, u32>;

	Process                 _process{};
    u32                     _update_mask{UINT32_MAX};
    std::vector<Address*>   _addresses_to_update{};
    AddressHandleMap        _address_ptr_to_handle{};
    AddressNames            _address_names{};
};



//region Template Implementation

template<typename T>
std::vector<uptr> Hack::scan(const T& value, uptr begin, usize size, usize max_results, bool threaded) const 
{ 
    return scan((const u8*)&value, sizeof(T), begin, size, max_results, false, threaded);
}

template<typename T>
void Hack::read(uptr ptr, T& dst) const 
{ 
    _process.read_memory(&dst, ptr, sizeof(T)); 
}

template<typename T>
void Hack::write(uptr ptr, const T& src) const 
{ 
    _process.write_memory(ptr, &src, sizeof(T)); 
}

template<typename T>
T Hack::read_value(uptr ptr) const 
{ 
    T result{}; 
    _process.read_memory(&result, ptr, sizeof(T));
    return result; 
}

template<typename T>
void Hack::write_value(uptr ptr, T src) const 
{ 
    _process.write_memory(ptr, &src, sizeof(T));    
}

//endregion

}

#endif
