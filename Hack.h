#pragma once

#include "Proc.h"
#include <assert.h>
#include <array>
#include <regex>
#include <string_view>
#include <unordered_map>
#include <list>
#include <vector>
#include <iostream>

struct Hack;

using PtrList = std::vector<Ptr>;

static constexpr size_t ADDRESS_VECTOR_SIZE = 8192;

static constexpr size_t SCAN_BLOCK_SIZE_BASIC = 256 * 1024;
static constexpr size_t SCAN_BLOCK_SIZE_STRING = 2 * 1024 * 1024;


struct Address {
	enum Type {
		STATIC, DYNAMIC, MANUAL
	};
	
	Type t{ STATIC };
	bool is_loaded{ false }, previous_holds_ptr{ true };
	uint16_t depth{ 0 }, backup_index{ UINT16_MAX }, update_mask{ UINT16_MAX }, update_index{ 0 };
	std::string name{}, module_name{};
	
	Ptr address{ 0 }, module_base_address{ 0 }, static_offset{ 0 };
	int64_t dynamic_offset{ 0 };

	Hack* hack{ nullptr };
	Address* previous{ nullptr };

	PtrPath path;
	std::vector<Address> backups;

	// Static address
	Address(Hack* hack, const std::string& name, const std::string& module_name, Ptr offset);

	// Dynamic address
	Address(Hack* hack, const std::string& name, Address& address, const PtrPath& offsets);

	// Manual address
	Address(Hack* hack, Ptr address);

	void add_backup(const std::string& depends_on, const PtrPath& offsets);
	void add_backup(Address& depends_on, const PtrPath& offsets);

	void load();

	bool is_valid();

	// Python read-only getters
	const Type get_type() const { return t; }
	const std::string& get_name() const { return name; }
	const std::string& get_module_name() const { return module_name; }
	bool get_is_loaded() const { return is_loaded; }
	Ptr get_address() const { return address; }
	Ptr get_module_base_address() const { return module_base_address; }
	Ptr get_static_offset() const { return static_offset; }
	Hack& get_hack() const { return *hack; }
	Address& get_previous() const { return *previous; }
	const PtrPath& get_offsets() const { return path; }
	// Offset modification
	void add_offsets(const PtrPath& offsets) { path.insert(path.end(), offsets.begin(), offsets.end()); }
	void pop_offsets(size_t n) { for (size_t i = 0; i < (n < path.size() ? n : path.size()); ++i) { path.pop_back(); } }

private:
	void load_from_next_backup();
};


class Buffer {
	uint8_t* _begin{ nullptr };
	size_t _size{ 0 }, _capacity{ 4 };
	bool _owns_memory{ true };
public:
	Hack* hack{ nullptr };

	// Owns memory
	explicit Buffer(size_t size = 4);

	// Does not own memory (C++ only)
	explicit Buffer(uint8_t* data, size_t size);

	// Does not own memory (src owns memory)
	Buffer(Buffer& src, Ptr offset, size_t size);

	~Buffer();

	bool owns_memory() const;

	uint8_t* data();

	const uint8_t* data() const;

	size_t size() const;

	Buffer* clear();

	Buffer* resize(size_t new_size);

	template<typename T>
	T read_basic(Ptr offset) const;

	template<typename T>
	void write_basic(Ptr offset, T src);

	template<typename T>
	const T& read_ptr_basic(Ptr offset) const;

	template<typename T>
	void write_ptr_basic(Ptr offset, T v) const;

	Buffer* read_buffer_ptr(Ptr offset, Buffer& v);

	Buffer* write_buffer_ptr(Ptr offset, Buffer& v);

	Buffer* read_slice(Ptr ptr, Ptr offset, size_t size);

	Buffer* write_slice(Ptr ptr, Ptr offset, size_t size);

	std::string read_string();

	void write_string(const std::string& v);

	// Copy/Move constructors
	Buffer(const Buffer& v);
	Buffer& operator=(const Buffer& v);

	Buffer(Buffer&& v) noexcept;
	Buffer& operator=(Buffer&& v) noexcept;
};


template<typename T>
struct Variable
{
	T storage{};
	Address* address{ nullptr };

	explicit Variable(Address& a);
	// Buffer constructors
	Variable(Address& a, size_t size);
	Variable(Buffer& src, Ptr offset, size_t size);

	const T& get() const;
	const T& read();
	void write(const T& v);
	// Buffer write
	void write_direct();
};


struct Hack {

	Process process{};
	uint16_t address_mask{ UINT16_MAX };
	std::string process_name{};

	std::list<std::vector<Address>> address_list;
	std::vector<Address*> addresses_to_update;
	std::unordered_map<std::string, Address*> name_to_address;

	Hack(const std::string& process_name);

	size_t get_architecture() const;

	Ptr get_module_base_address(const std::string& module_name) const { return process.get_module_base_address(module_name); }

	bool is_attached() const { return process.is_attached(); }

	Ptr max_ptr() const { return 0xFFFFFFFFFFFFFFFF >> (process.ptr_t == PointerType::BIT32 ? 32 : 0); }

	const ModuleMap& modules() const { return process.modules; }
	
	size_t pid() const { return process.pid(); }

	size_t ptr_size() const { return process.ptr_t == PointerType::BIT32 ? 4 : 8; }


	// Addresses
	Address& address(const std::string& name);

	Address& add_static_address(const std::string& name, const std::string& module_name, Ptr offset);

	Address& add_dynamic_address(const std::string& name, Address& depends_on, const PtrPath& offsets);

	Address& add_dynamic_address(const std::string& name, const std::string& depends_on, const PtrPath& offsets);

	Address& get_or_add_dynamic_address(const std::string& name, Address& depends_on, const PtrPath& offsets);

	Address manual_address(Ptr address);

	void clear_addresses();

	// Attach/load
	void attach();
	void load_addresses();

	// Memory read/write
	Ptr follow_ptr_path(Ptr start, const PtrPath& offsets, bool start_is_address_of_ptr = true) const;

	Ptr scan_char(Ptr start, uint8_t value, size_t max_steps) const;

	template<typename T>
	PtrList scan(T value, Ptr begin, size_t size, size_t n_results) const;

	template<typename T>
	void read_memory(Ptr ptr, T& dst) const { process.read_memory(&dst, ptr, sizeof(T)); }

	template<typename T>
	void write_memory(Ptr ptr, const T& src) const { process.write_memory(ptr, &src, sizeof(T)); }

	template<typename T>
	T read_memory_basic(Ptr ptr) const { T result{}; process.read_memory(&result, ptr, sizeof(T)); return result; }

	template<typename T>
	void write_memory_basic(Ptr ptr, T src) const { process.write_memory(ptr, &src, sizeof(T)); }

	// Buffer specializations
	template<>
	void read_memory<Buffer>(Ptr ptr, Buffer& dst) const { process.read_memory(dst.data(), ptr, dst.size()); }

	template<>
	void write_memory<Buffer>(Ptr ptr, const Buffer& src) const { process.write_memory(ptr, src.data(), src.size()); }

	void read_slice(Ptr ptr, Buffer& dst, Ptr offset, size_t size) const;

	void write_slice(Ptr ptr, const Buffer& src, Ptr offset, size_t size) const;

	void read_buffer_ptr(Buffer& src, Ptr offset, Buffer& dst) const;

	void write_buffer_ptr(Buffer& src, Ptr offset, Buffer& dst) const;

private:
	template<typename... Args>
	Address& add_address(Args&&... args);

	void sort_addresses_to_update();

	void turn_off_address_flag_bits(Address& addr, uint16_t bits);
};

// MARK: Buffer implementation

template<typename T>
T Buffer::read_basic(Ptr offset) const
{ 
	T result{}; 
	memcpy(&result, data() + offset, sizeof(T)); 
	return result; 
}

template<typename T>
void Buffer::write_basic(Ptr offset, T src)
{ 
	memcpy(data() + offset, &src, sizeof(T));
}

template<typename T>
const T& Buffer::read_ptr_basic(Ptr offset) const
{
	Ptr ptr = read_basic<Ptr>(offset);
	return hack->read_memory_basic<T>(ptr);
}

template<typename T>
void Buffer::write_ptr_basic(Ptr offset, T v) const
{
	Ptr ptr = read_basic<Ptr>(offset);
	hack->write_memory_basic<T>(ptr, v);
}


// MARK: Hack Implementation
template<typename... Args>
Address& Hack::add_address(Args&&... args)
{
	if (address_list.back().size() >= address_list.back().capacity()) {
		address_list.emplace_back();
		address_list.back().reserve(ADDRESS_VECTOR_SIZE);
	}
	address_list.back().emplace_back(std::forward<Args>(args)... );
	return address_list.back().back();
}

template<typename T>
void scan_basic(const Hack& h, T value, Ptr begin, size_t size, size_t n_results, PtrList& results)
{
	h.process.iter_regions(begin, size, [value, n_results, r=&results](Ptr rbegin, size_t rsize, uint8_t* data) {
		T* memory = reinterpret_cast<T*>(data);
		for (size_t i = 0; i < rsize; ++i) {
			if (memory[i] == value) {
				r->push_back(rbegin + i * sizeof(T));
				if (n_results && r->size() >= n_results) {
					return true;
				}
			}
		}
		return false;

	}, SCAN_BLOCK_SIZE_BASIC);
}

inline void scan_regex(const Hack& h, const std::string& value, Ptr begin, size_t size, size_t n_results, PtrList& results)
{
	h.process.iter_regions(begin, size, [value, n_results, r = &results](Ptr rbegin, size_t rsize, uint8_t* data) {
		std::string_view bytes{ (char*)data, rsize };

		std::regex reg(value);
		auto matches_begin = std::cregex_iterator(bytes.data(), bytes.data() + bytes.size(), reg);
		auto matches_end = std::cregex_iterator();

		for (auto i = matches_begin; i != matches_end; ++i) {
			r->push_back(rbegin + i->position());
			if (n_results && r->size() >= n_results) {
				return true;
			}
		}
		return false;

	}, SCAN_BLOCK_SIZE_STRING);
}

template<typename T>
PtrList Hack::scan(T value, Ptr begin, size_t size, size_t n_results) const
{
	PtrList results;
	if constexpr (std::is_same_v<T, std::string>) {
		scan_regex(*this, value, begin, size, n_results, results);
	}
	else {
		scan_basic(*this, value, begin, size, n_results, results);
	}
	return results;
}


// MARK: Variable Implementation

template<typename T>
Variable<T>::Variable(Address& a) 
	: address(&a)  
{}

template<typename T>
const T& Variable<T>::get() const 
{ 
	return storage; 
}

template<typename T>
const T& Variable<T>::read() 
{
	if (address) {
		if constexpr (std::is_same_v<T, Buffer>) {
			if (storage.owns_memory()) {
				storage.hack->read_memory<Buffer>(address->address, storage);
			}
		}
		else {
			address->hack->read_memory<T>(address->address, storage);
		}
	}
	return get();
}


template<typename T>
void Variable<T>::write(const T& v) 
{
	storage = v;
	write_direct();
}

template<typename T>
void Variable<T>::write_direct()
{
	if (!address) { return; }
	if constexpr (std::is_same_v<T, Buffer>) {
		storage.hack->write_memory<Buffer>(address->address, storage);
	}
	else {
		address->hack->write_memory<T>(address->address, storage);
	}
}

// Buffer

template<typename T>
Variable<T>::Variable(Address& a, size_t size)
	:	storage{ size }, 
		address(&a) 
{ 
	storage.hack = address->hack;
	address->previous_holds_ptr = false; 
}

template<typename T>
Variable<T>::Variable(Buffer& src, Ptr offset, size_t size)
	:	storage{ src, offset, size }, 
		address(nullptr) 
{
	storage.hack = src.hack;
}
