#include "Address.h"
#include "Hack.h"

#include <cassert>

namespace pygamehack {

Address::Address(Hack& hack):
    _hack{&hack},
    _type{u64(Type::MANUAL)},
    _is_loaded{false},
    _auto_updates{false},
    _name_handle{0},
    _update_mask{UPDATE_ALL}
{}

Address::~Address()
{
    stop_auto_update();
    if (_name_handle != 0)
        _hack->address_names().remove(_name_handle);
}

Address::Address(const Address& v):
    _hack{v._hack},
    _address{v._address},
    _type{v._type},
    _is_loaded{v._is_loaded},
    _auto_updates{false},
    _name_handle{v.name().empty() ? 0u : _hack->address_names().add(v.name())},
    _update_mask{v._update_mask}
{
    if (type() == Address::Type::STATIC) { _static = v._static; }
    else if (type() == Address::Type::DYNAMIC) { _dynamic = v._dynamic; }
    if (v._auto_updates) { auto_update(); }
}

Address& Address::operator=(const Address& v)
{
	if (&v != this) {
        _hack = v._hack;
        _address = v._address;
        _type = v._type;
        _is_loaded = v._is_loaded;
        _auto_updates = false;
        _name_handle = v.name().empty() ? 0u : _hack->address_names().add(v.name());
        _update_mask = v._update_mask;
        if (type() == Address::Type::STATIC) { _static = v._static; }
        else if (type() == Address::Type::DYNAMIC) { _dynamic = v._dynamic; }
        if (v._auto_updates) { auto_update(); }
    }
	return *this;
}

Address::Address(Address&& v) noexcept :
    _hack{v._hack},
    _address{v._address},
    _type{v._type},
    _is_loaded{v._is_loaded},
    _auto_updates{false},
    _name_handle{v._name_handle},
    _update_mask{v._update_mask}
{
    if (type() == Address::Type::STATIC) { _static = v._static; }
    else if (type() == Address::Type::DYNAMIC) { _dynamic = v._dynamic; }
    v._name_handle = 0;
    if (v._auto_updates) { auto_update(); }
}

Address& Address::operator=(Address&& v) noexcept
{
	if (&v != this) {
        _hack = v._hack;
        _address = v._address;
        _type = v._type;
        _is_loaded = v._is_loaded;
        _auto_updates = false;
        _name_handle = v._name_handle;
        _update_mask = v._update_mask;
        if (type() == Address::Type::STATIC) { _static = v._static; }
        else if (type() == Address::Type::DYNAMIC) { _dynamic = v._dynamic; }
        v._name_handle = 0;
        if (v._auto_updates) { auto_update(); }
    }
	return *this;
}

Address Address::Manual(Hack& hack, uptr address)
{
    Address a{hack};
    a._address = address;
    a._is_loaded = true;
    new (a._storage) StaticAddressData;
    return a;
}

Address Address::Static(Hack& hack, const string& module_name, uptr offset)
{
    Address a{hack};
    a._type = u64(Type::STATIC);
    new (a._storage) StaticAddressData;
    a._static.offset = offset;
    a._static.module_name = module_name;
    return a;
}

Address Address::Dynamic(Address& parent, const uptr_path& offsets, bool add_first_offset_to_parent_address)
{
    Address a{*parent._hack};
    a._type = u64(Type::DYNAMIC);
    new (a._storage) DynamicAddressData;
    a._dynamic.parent = &parent;
    a._dynamic.offsets = offsets;
    return a;
}

Address Address::CreateDynamic(Address& parent, const u32* offsets, usize n_offsets, bool add_first_offset_to_parent_address)
{
    Address a{*parent._hack};
    a._type = u64(Type::DYNAMIC);
    new (a._storage) DynamicAddressData;
    a._dynamic.parent = &parent;
    a._dynamic.offsets.reserve(n_offsets);
    for (const auto* it = offsets; it < offsets + n_offsets; ++it) { a._dynamic.offsets.push_back(*it); }
    return a;
}

Hack& Address::hack()
{
    return *_hack;
}

bool Address::loaded() const
{
    return bool(_is_loaded);
}

const Address& Address::parent() const
{
    PGH_ASSERT(type() == Type::DYNAMIC, "Only dynamic addresses can have a parent address");
    return *_dynamic.parent;
}

Address::Type Address::type() const
{
    return Type(_type);
}

bool Address::valid() const
{
    u8 v{};
    return _hack->process().read_memory(&v, _address, 1u);
}

uptr Address::value() const
{
    return _address;
}

const uptr_path& Address::offsets() const
{
    PGH_ASSERT(type() == Type::DYNAMIC, "Only dynamic addresses can have an offset path");
    return _dynamic.offsets;
}

void Address::add_offsets(const uptr_path& offsets)
{
    PGH_ASSERT(type() == Type::DYNAMIC, "Only dynamic addresses can have an offset path");
    _dynamic.offsets.insert(_dynamic.offsets.end(), offsets.begin(), offsets.end());
}

void Address::pop_offsets(usize n)
{
    PGH_ASSERT(type() == Type::DYNAMIC, "Only dynamic addresses can have an offset path");
    PGH_ASSERT(n == 0 || n <= _dynamic.offsets.size(), "Popping too many offsets");
    n == 0 
        ? _dynamic.offsets.clear()
        : _dynamic.offsets.erase(_dynamic.offsets.end() - n, _dynamic.offsets.end());
}

uptr Address::load()
{
    if (type() == Type::STATIC) {
        _address = _hack->process().get_base_address(_static.module_name) + _static.offset;
        _is_loaded = _address != _static.offset;
    }
    else if (type() == Type::DYNAMIC) {
        if (!_dynamic.parent->loaded()) _dynamic.parent->load();
        _address = _hack->process().follow(_dynamic.parent->value(), _dynamic.offsets);
        _is_loaded = _address != 0;
    }
    
    return _address;
}

const string& Address::name() const
{
    return _hack->address_names().get(_name_handle);
}

void Address::set_name(const string& v)
{
    if (!v.empty() && _name_handle == 0) {
        _name_handle = _hack->address_names().add(v);
    }
    else if (!v.empty() && _name_handle != 0) {
        _hack->address_names().set(_name_handle, v);
    }
    else if (v.empty()) {
        if (_name_handle != 0) {
            _hack->address_names().remove(_name_handle);
        }
        _name_handle = 0;
    }
}

Address& Address::auto_update()
{
    if (!_auto_updates) {
        _auto_updates = true;
        _hack->start_auto_update(*this);
    }
    return *this;
}

void Address::stop_auto_update()
{
    if (_auto_updates) {
        _hack->stop_auto_update(*this);
        _auto_updates = false;
    }
}

void Address::set_update_mask(u32 mask)
{
    _update_mask = mask;
}

const string& Address::module_name() const
{
    PGH_ASSERT(type() == Address::Type::STATIC, "Can only access module_name on STATIC addresses");
    return _static.module_name;
}

uptr Address::module_offset() const
{
    PGH_ASSERT(type() == Address::Type::STATIC, "Can only access module_offset on STATIC addresses");
    return _static.offset;
}

bool Address::operator==(const Address& other) const
{
    return _type == other._type && _address == other._address;
}

bool Address::operator!=(const Address& other) const
{
    return !(*this == other);
}

const Process& Address::process() const
{
    return _hack->process();
}

void Address::unload()
{
    _address = 0;
    _is_loaded = false;
}

void Address::update(u32 mask)
{
    if ((u32(_update_mask) & mask) != 0)
        load();
}


const string& AddressNames::get(u32 handle) const
{
    return strings[handle];
}

void AddressNames::set(u32 handle, const string& v)
{
    strings[handle] = v;
}

u32 AddressNames::add(const string& v)
{
    if (free_slots.empty()) {
        const u32 handle = strings.size();
        strings.emplace_back(v);
        return handle;
    }
    else {
        const u32 handle = free_slots.back();
        free_slots.pop_back();
        strings[handle] = v;
        return handle;
    }
}

void AddressNames::remove(u32 handle)
{
    free_slots.push_back(handle);
    strings[handle].clear();
}

}
