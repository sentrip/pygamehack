#include "Hack.h"

#include <algorithm>
#include <iostream>


// MARK: Address

static inline bool in_parent_hierarchy(Address* parent, Address* child)
{
	if (parent == child) { return true; }
	while (child && child->depth > parent->depth) {
		child = child->previous;
		if (parent == child) { return true; }
	}
	return false;
}

// Static address
Address::Address(Hack* hack, const std::string& name, const std::string& module_name, Ptr offset)
	: t(STATIC), previous_holds_ptr{ true }, depth(0), name(name), module_name(module_name), static_offset(offset), hack(hack)
{}

// Dynamic address
Address::Address(Hack* hack, const std::string& name, Address& address, const PtrPath& offsets)
	: t(DYNAMIC), previous_holds_ptr{ true }, depth(address.depth + 1), name(name), hack(hack), previous(&address), path(offsets)
{}

Address::Address(Hack* hack, Ptr address)
	: t(MANUAL), previous_holds_ptr{ true }, depth(0), static_offset(address), hack(hack)
{}

void Address::add_backup(const std::string& depends_on, const PtrPath& offsets)
{
	add_backup(hack->address(depends_on), offsets);
}

void Address::add_backup(Address& depends_on, const PtrPath& offsets)
{
	std::string backup_name = name + "_backup_" + std::to_string(backups.size());
	backups.emplace_back(hack, backup_name, depends_on, offsets);
}


void Address::load() 
{
	if (t == STATIC) {
		module_base_address = hack->process.get_module_base_address(module_name.c_str());
		address = module_base_address + static_offset;
	}
	else if (t == DYNAMIC) {
		address = hack->follow_ptr_path(previous->address, path, previous->previous_holds_ptr) + static_cast<Ptr>(dynamic_offset);
		// If the address is no longer valid try to load any backup addresses
		if (address < UINT16_MAX && !backups.empty()) {
			load_from_next_backup();
		}
	}
	else {
		hack->read_memory<Ptr>(static_offset, address);
		address = hack->follow_ptr_path(address, path, true) + static_cast<Ptr>(dynamic_offset);
	}
	is_loaded = true;
}

bool Address::is_valid()
{
	bool v = true;
	return address > UINT16_MAX && hack->process.read_memory(&v, address, 1);
}

void Address::load_from_next_backup()
{
	Ptr expected_useless_address = address;
	// If using backups for the first time set the index
	if (backup_index == UINT16_MAX) {
		backup_index = 0;
	}
	// Load next available backup
	backups[backup_index].load();
	address = backups[backup_index].address;
	while (address == expected_useless_address && backup_index < UINT16_MAX) {
		address = backups[backup_index].address;
		backup_index++;
	}
}


// MARK: Buffer

Buffer::Buffer(size_t size) 
	:	_begin{ (uint8_t*)malloc(size) },
		_size{size},
		_capacity{size},
		_owns_memory{true}
{
	clear();
}

Buffer::Buffer(uint8_t* data, size_t size)
	:	_begin{ data },
		_size{ size },
		_capacity{ size },
		_owns_memory{ false }
{
}

Buffer::Buffer(Buffer& src, Ptr begin, size_t size)
	:	_begin{ src._begin + begin },
		_size{ size },
		_capacity{size},
		_owns_memory{ false }
{}

Buffer::~Buffer()
{
	if (_owns_memory && _begin) {
		free(_begin);
	}
}

bool Buffer::owns_memory() const
{
	return _owns_memory;
}

uint8_t* Buffer::data()
{ 
	return _begin;
}

const uint8_t* Buffer::data() const
{
	return _begin;
}

size_t Buffer::size() const 
{ 
	return _size;
}

Buffer* Buffer::clear()
{
	memset(_begin, 0, _capacity);
	return this;
}

Buffer* Buffer::resize(size_t new_size)
{
	if (_owns_memory && _capacity != new_size)  {
		_begin = (uint8_t*)realloc(_begin, new_size);
		_capacity = new_size;
		clear();
	}
	_size = new_size;
	return this;
}

Buffer* Buffer::read_buffer_ptr(Ptr offset, Buffer& v)
{
	hack->read_buffer_ptr(*this, offset, v);
	return this;
}

Buffer* Buffer::write_buffer_ptr(Ptr offset, Buffer& v)
{
	hack->write_buffer_ptr(*this, offset, v);
	return this;
}

Buffer* Buffer::read_slice(Ptr ptr, Ptr offset, size_t size)
{
	hack->read_slice(ptr, *this, offset, size);
	return this;
}

Buffer* Buffer::write_slice(Ptr ptr, Ptr offset, size_t size)
{
	hack->write_slice(ptr, *this, offset, size);
	return this;
}

std::string Buffer::read_string()
{
	return std::string{ (char*)_begin, _size };
}

void Buffer::write_string(const std::string& v)
{
	resize(v.size());
	memcpy(_begin, v.c_str(), v.size());
}

Buffer::Buffer(const Buffer& v)
	:	_begin{ (uint8_t*)malloc(v._capacity) },
		_size{ v._size },
		_capacity{v._capacity},
		_owns_memory{ true }
{
	memcpy(_begin, v._begin, _size < v._size ? _size : v._size);
}

Buffer& Buffer::operator=(const Buffer& v)
{
	_size = _size < v._size ? _size : v._size;
	memcpy(_begin, v._begin, _size);
	return *this;
}

Buffer::Buffer(Buffer&& v) noexcept
	:	_begin{ v._begin },
		_size{ v._size },
		_capacity{v._capacity},
		_owns_memory{ v._owns_memory }
{
	v._begin = nullptr;
	v._size = 0;
	v._capacity = 0;
	v._owns_memory = false;
}

Buffer& Buffer::operator=(Buffer&& v) noexcept
{
	_begin = v._begin;
	_size = v._size;
	_capacity = v._capacity;
	_owns_memory = v._owns_memory;
	v._begin = nullptr;
	v._size = 0;
	v._capacity = 0;
	v._owns_memory = false;
	return *this;
}



// MARK: Hack

Hack::Hack(const std::string& process_name)
	: process_name(process_name) 
{ 
	address_list.emplace_back();
	address_list.back().reserve(ADDRESS_VECTOR_SIZE);
}

size_t Hack::get_architecture() const
{
	if (!process.is_attached()) {
		throw std::exception{"Must attach to process before checking the architecture"};
	}
	return process.ptr_t == PointerType::BIT32 ? 32 : 64;
}

Address& Hack::address(const std::string& name) 
{
	return *name_to_address.at(name);
}

Address& Hack::add_static_address(const std::string& name, const std::string& module_name, Ptr offset) 
{
	Address& addr = add_address(this, name, module_name, offset);
	name_to_address[name] = &addr;
	return addr;
}

Address& Hack::add_dynamic_address(const std::string& name, Address& depends_on, const PtrPath& offsets) 
{
	Address& addr = add_address(this, name, depends_on, offsets);
	name_to_address[name] = &addr;
	addresses_to_update.push_back(&addr);
	sort_addresses_to_update();
	return addr;
}

Address& Hack::add_dynamic_address(const std::string& name, const std::string& depends_on, const PtrPath& offsets) 
{
	return add_dynamic_address(name, *name_to_address.at(depends_on), offsets);
}

Address& Hack::get_or_add_dynamic_address(const std::string& name, Address& depends_on, const PtrPath& offsets)
{
	if (auto it = name_to_address.find(name);
		it != name_to_address.end())
	{
		return *(it->second);
	}
	else {
		return add_dynamic_address(name, depends_on, offsets);
	}
}

Address Hack::manual_address(Ptr address)
{
	return Address{ this, address };
}

void Hack::clear_addresses()
{
	address_list.clear();
	addresses_to_update.clear();
	name_to_address.clear();
}

void Hack::attach() 
{
	if (!process.is_attached() || process_name != process.name) {
		process.attach(process_name);
		assert(process.is_attached());
	}

	for (auto it = address_list.begin(); it != address_list.end(); ++it) {
		for (auto& a : *it) {
			if (a.t == Address::STATIC) {
				a.load();
			}
		}
	}
}

void Hack::load_addresses() 
{
	for (auto it = address_list.begin(); it != address_list.end(); ++it) {
		for (auto& a : *it) {
			if (a.t == Address::DYNAMIC) {
				a.is_loaded = false;
			}
			else if (!a.is_loaded) {
				a.load();
			}
		}
	}

	for (auto* a : addresses_to_update) {
		assert(a->previous->is_loaded);
		a->update_mask |= a->previous->update_mask;
		if (address_mask & a->update_mask) {
			a->load();
		}
	}
}

Ptr Hack::follow_ptr_path(Ptr start, const PtrPath& offsets, bool start_is_address_of_ptr) const
{
	return process.follow_ptr_path(start, offsets, start_is_address_of_ptr);
}

Ptr Hack::scan_char(Ptr start, uint8_t value, size_t max_steps) const
{
	for (Ptr p = start; p < start + max_steps; ++p) {
		if (read_memory_basic<uint8_t>(p) == value) {
			return p;
		}
	}
	return 0;
}

void Hack::read_slice(Ptr ptr, Buffer& dst, Ptr offset, size_t size) const 
{ 
	process.read_memory(dst.data() + offset, ptr + offset, dst.size() <= (offset + size) ? size : dst.size() - offset); 
}

void Hack::write_slice(Ptr ptr, const Buffer& src, Ptr offset, size_t size) const 
{ 
	process.write_memory(ptr + offset, src.data() + offset, src.size() <= (offset + size) ? size : src.size() - offset);
}

void Hack::read_buffer_ptr(Buffer& src, Ptr offset, Buffer& dst) const 
{
	Ptr ptr = src.read_basic<Ptr>(offset);
	read_memory<Buffer>(ptr, dst);
}

void Hack::write_buffer_ptr(Buffer& src, Ptr offset, Buffer& dst) const
{
	Ptr ptr = src.read_basic<Ptr>(offset);
	write_memory<Buffer>(ptr, dst);
}

void Hack::sort_addresses_to_update() 
{
	std::sort(addresses_to_update.begin(), addresses_to_update.begin(), [](auto* lhs, auto* rhs) { return lhs->depth < rhs->depth; });
	for (size_t i = 0; i < addresses_to_update.size(); ++i)
	{
		addresses_to_update[i]->update_index = i;
	}
}

void Hack::turn_off_address_flag_bits(Address& addr, uint16_t bits)
{
	addr.update_mask &= bits;

	if (addr.t == Address::STATIC) {
		return;
	}

	for (size_t i = addr.update_index + 1; i < addresses_to_update.size(); ++i) {
		Address* child = addresses_to_update[i];
		if (in_parent_hierarchy(&addr, child)) {
			child->update_mask &= bits;
		}
	}
}