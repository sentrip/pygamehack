
#ifndef PYGAMEHACK_ADDRESS_H
#define PYGAMEHACK_ADDRESS_H

#include "config.h"
#include <algorithm>
#include <vector>

namespace pygamehack {

using uptr_path = std::vector<u32>;


struct DynamicAddressData {
    Address*    parent{};
    uptr_path   offsets;
};


struct StaticAddressData {
    uptr        offset{ 0 };
    string      module_name;
};


class Address {
public:
    enum class Type { MANUAL, STATIC, DYNAMIC };
    static constexpr u32 UPDATE_ALL = UINT32_MAX;

    // C++ Only
    explicit Address(Hack& hack);
    ~Address();
    
    // Constructors
    static Address      Manual(Hack& hack, uptr address);
    static Address      Static(Hack& hack, const string& module_name, uptr offset);
    static Address      Dynamic(Address& parent, const uptr_path& offsets, bool add_first_offset_to_parent_address = false);

    // Properties
    Hack&               hack();
    bool                loaded() const;
    const Address&      parent() const;
    Type                type() const;
    bool                valid() const;
    uptr                value() const;
    
    // (Dynamic) Offsets/Load
    const uptr_path&    offsets() const;
    void                add_offsets(const uptr_path& offsets);
	void                pop_offsets(usize n);
    uptr                load();

    // Auto Update
    Address&            auto_update();
    void                stop_auto_update();
    void                set_update_mask(u32 mask = UPDATE_ALL);

    // Name
    const string&       name() const;
    void                set_name(const string& name);

    // (Static) Module Name/Offset
    const string&       module_name() const;
    uptr                module_offset() const;

	// Copy/Move constructors and operators
public:
	Address(const Address& v);
	Address& operator=(const Address& v);

	Address(Address&& v) noexcept;
	Address& operator=(Address&& v) noexcept;

    bool operator==(const Address& other) const;
    bool operator!=(const Address& other) const;

    // C++
    // This constructor is to avoid copying vectors when creating addresses from a cheat engine pointer scan file
    static Address CreateDynamic(Address& parent, const u32* offsets, usize n_offsets, bool add_first_offset_to_parent_address);
    const Process& process() const;
    void unload();
    void update(u32 mask);

private:
    Hack*           _hack{};
    uptr            _address{ 0 };
    u64             _type: 2;
    u64             _is_loaded: 1;
    u64             _auto_updates: 1;
    u64             _name_handle: 28;
    u64             _update_mask: 32;

    union {
        u8 _storage[std::max<usize>(sizeof(StaticAddressData), sizeof(DynamicAddressData))]{};
        StaticAddressData _static;
        DynamicAddressData _dynamic;
    };
};


class AddressNames {
public:
    AddressNames() = default;
    
    const string&   get(u32 handle) const;
    void            set(u32 handle, const string& v);
    u32             add(const string& v);
    void            remove(u32 handle);

private:
    std::vector<u32> free_slots;
    std::vector<string> strings;
};

}

#endif
