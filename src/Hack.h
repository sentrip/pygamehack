
#ifndef PYGAMEHACK_HACK_H
#define PYGAMEHACK_HACK_H

#include "Process.h"
#include "Address.h"

namespace pygamehack {

class Hack {
public:
    class Scan;
    using ScanModifyLoopFunc = std::function<bool(Scan&)>;

    Hack();

    // Properties
    const Process&      process() const;

    // Attach/detach
    void                attach(u32 process_id);
    void                attach(const string& process_name);
    void                detach();

	// Memory scan
	uptr                find(i8 value, uptr begin, usize size) const;
    
    std::vector<uptr>   scan(Scan& scan) const;

    std::vector<uptr>   scan_modify_loop(Scan& scan, ScanModifyLoopFunc&& modify) const;

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

    // Scan
public:
    class Scan {
    public:
        template<typename T>
        explicit Scan(T data, uptr begin, usize size, usize max_results = 0, bool read = true, bool write = false, bool execute = false, bool threaded = true);

        explicit Scan(const string& data, uptr begin, usize size, usize max_results = 0, bool read = true, bool write = false, bool execute = false, bool regex = false, bool threaded = true);

        void set_value(const string& data);

        uptr begin{};
        usize size{};
        usize value_size{};
        usize max_results{};
        bool read{};
        bool write{};
        bool execute{};
        bool regex{};
        bool threaded{};

        // C++ only
    public:
        Scan(u64 type_hash, const u8* data, usize value_size, uptr begin, usize size, usize max_results = 0, bool read = true, bool write = false, bool execute = false, bool regex = false, bool threaded=false);
        ~Scan();
        const u64 type_id() const;
        const u8* data() const;
        void set_value(u64 type_hash, const u8* data, usize value_size);

    private:
        static constexpr u64 BUFFER_SIZE = 64;
        u8 buffer[BUFFER_SIZE]{};
        u8* ptr{};
        u8 value_type{};
        u64 type_hash{};
    };

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
    std::vector<uptr>   scan_reduce(const std::vector<uptr>& results, const Scan& scan) const;

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


template<typename T>
Hack::Scan::Scan(T data, uptr begin, usize size, usize max_results, bool read, bool write, bool execute, bool threaded):
    Scan{typeid(T).hash_code(), (const u8*)&data, sizeof(T), begin, size, max_results, read, write, execute, false, threaded}
{}

//endregion

}

#endif
