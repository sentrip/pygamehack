#include "Hack.h"
#include "Address.h"
#include "Buffer.h"

#include <cassert>
#include <iostream>
#include <regex>
#include <fstream>
#include <filesystem>
#include <execution>

#include <thread>
#include <mutex>
#include <atomic>


namespace pygamehack {

//region Memory Scan

static Process::iter_region_callback process_region_func(std::vector<uptr>& results, const Process& process, const u8* value, usize value_size, uptr begin, usize size, usize max_results, bool regex, std::mutex* mutex)
{
    if (regex) {
        // TODO: Fast regex scan
        return [value, value_size, max_results, &results, mutex](uptr rbegin, usize rsize, const u8* data) {
            std::string_view bytes{ (const char*)data, rsize };
            std::string value_bytes{ (const char*)value, value_size };

            std::regex reg(value_bytes);
            auto matches_begin = std::cregex_iterator(bytes.data(), bytes.data() + bytes.size(), reg);
            auto matches_end = std::cregex_iterator();

            for (auto i = matches_begin; i != matches_end; ++i) {
                if (mutex) {
                    std::unique_lock<std::mutex> lock{*mutex};
                    results.push_back(rbegin + i->position());
                    if (max_results && results.size() >= max_results) {
                        return true;
                    }
                }
                else {
                    results.push_back(rbegin + i->position());
                    if (max_results && results.size() >= max_results) {
                        return true;
                    }
                }
            }
            return false;

        };
    }
    else {
        return [value, value_size, max_results,&results, mutex](uptr rbegin, usize rsize, const u8* data) {
            for (size_t i = 0; i < rsize; i += value_size) {
                if (memcmp(&data[i], value, std::min<usize>(rsize - i, value_size)) == 0) {
                    if (mutex) {
                        std::unique_lock<std::mutex> lock{*mutex};
                        results.push_back(rbegin + i * value_size);
                        if (max_results && results.size() >= max_results) {
                            return true;
                        }
                    }
                    else {
                        results.push_back(rbegin + i * value_size);
                        if (max_results && results.size() >= max_results) {
                            return true;
                        }
                    }
                }
            }
            return false;

        };
    }
}

static void do_fast_memory_scan(usize n_threads, std::vector<uptr>& results, const Process& process, const u8* value, usize value_size, uptr begin, usize size, usize max_results, bool regex)
{
    static constexpr size_t SCAN_BLOCK_SIZE_BASIC = 256 * 1024;
    static constexpr size_t SCAN_BLOCK_SIZE_STRING = 2 * 1024 * 1024;
    static constexpr size_t MIN_SCAN_SIZE_FOR_THREADING = 2 * 1024 * 1024;
    static constexpr size_t MIN_SCAN_REGIONS_PER_THREAD = 32;

    struct ScanRegion {
        uptr begin{};
        usize size{};
    };

    if (n_threads == 0 || size <= MIN_SCAN_SIZE_FOR_THREADING) {
        process.iter_regions(begin, size, process_region_func(results, process, value, value_size, begin, size, max_results, regex, nullptr));
        return;
    }

    std::vector<ScanRegion> queue;
    
    // Collect scan regions
    usize block_size = regex ? SCAN_BLOCK_SIZE_STRING : SCAN_BLOCK_SIZE_BASIC;
    process.iter_regions(begin, size, 
        [&queue](uptr rbegin, usize rsize, const u8* data) { queue.push_back(ScanRegion{rbegin, rsize}); return false; },
        Memory::Protect::NONE, false, block_size);

    // Determine number of threads based on number of scan regions
    n_threads = std::max<usize>(n_threads, 1 + (queue.size() / MIN_SCAN_REGIONS_PER_THREAD));
    
    // Ensure we only use as many threads as are available
    n_threads = std::min<usize>(n_threads, std::thread::hardware_concurrency());

    std::mutex mutex;
    std::vector<std::thread> threads;
    std::atomic_bool done{false};
    std::atomic_uint64_t scan_index{0};
    threads.resize(n_threads);

    // Create region process function
    auto do_process = process_region_func(results, process, value, value_size, begin, size, max_results, regex, &mutex);

    // Dispatch scans to threads
    for (usize i = 0; i < n_threads; ++i) {
        threads[i] = std::thread([&do_process, &process, &queue, &scan_index, &done, block_size=block_size]()
        {
            Memory mem;
            ScanRegion region;
            std::vector<u8> data;
            data.resize(block_size);

            while (!done.load(std::memory_order_acquire))
            {
                const u64 i = scan_index.fetch_add(1, std::memory_order_relaxed);
                if (i >= queue.size()) {
                    done.store(true, std::memory_order_release);
                    return;
                }

                region = queue[i];
                
                if (region.size > data.size()) data.resize(region.size);

                mem = process.protect(region.begin, region.size, Memory::Protect::READ_WRITE);
                
                process.read_memory(data.data(), region.begin, region.size);

                mem.protect();
                
                if (do_process(region.begin, region.size, data.data())) {
                    done.store(true, std::memory_order_release);
                    mem.reset();
                    return;
                }

                mem.reset();
            }
        });
    }
    
    // Wait for threads to finish
    for (auto& thread: threads) {
        thread.join();
    }
}

static void do_fast_memory_scan_reduce(usize n_threads, std::vector<uptr>& results, const std::vector<uptr>& previous_results, const Process& process, const u8* value, usize value_size, bool regex)
{
    PGH_ASSERT(value_size <= 64, "No support for scan_modify_loop with large strings (>=64)");

    n_threads = 0; // TODO: Threaded memory scan reduce

    if (n_threads == 0) {
        results.reserve(previous_results.size());

        u8 buffer[64]{};
        for (const uptr r: previous_results) {
            process.read_memory(buffer, r, value_size);
            if (memcmp(value, buffer, value_size) == 0) {
                results.push_back(r);
            }
        }
        return;
    }
}

//endregion

//region Hack

Hack::Hack()
{
    // Add empty string that default-constructed addresses can return as their name
    _address_names.add("");
}

const Process& Hack::process() const
{
    return _process;
}

void Hack::attach(u32 process_id)
{
    if (!_process.attach(process_id)) {
        std::cerr << "Failed to attach to process: " << process_id << "\n";
    }
}

void Hack::attach(const string& process_name)
{
    if (!_process.attach(process_name)) {
        std::cerr << "Failed to attach to process: " << process_name << "\n";
    }
}

void Hack::detach()
{
    _process.detach();
}

uptr Hack::find(i8 value, uptr begin, usize size) const
{
    return _process.find_char(value, begin, size);
}

std::vector<uptr> Hack::scan(Scan& scan) const
{
    std::vector<uptr> results;
    do_fast_memory_scan(usize(scan.threaded), results, _process, scan.data(), scan.value_size, scan.begin, scan.size, scan.max_results, scan.regex);
    return results;
}

std::vector<uptr> Hack::scan_reduce(const std::vector<uptr>& results, const Scan& scan) const
{
    std::vector<uptr> merged_results;
    do_fast_memory_scan_reduce(usize(scan.threaded), merged_results, results, _process, scan.data(), scan.value_size, scan.regex);
    return merged_results;
}

std::vector<uptr> Hack::scan_modify(Hack::Scan& scan, ScanModifyLoopFunc&& modify) const
{
    bool should_continue = false;
    std::vector<uptr> results, reduced_results;
    usize n_threads = usize(scan.threaded);
    usize value_size = scan.value_size;
    results = this->scan(scan);
    while (true) {
        if (should_continue) std::swap(results, reduced_results);
        should_continue = modify(scan);
        do_fast_memory_scan_reduce(n_threads, reduced_results, results, _process, scan.data(), value_size, scan.regex);
        if (!should_continue) break;
    }

    return reduced_results;
}

void Hack::start_auto_update(Address& address)
{
    if (address.type() == Address::Type::MANUAL) return;

    // Acquire lock

    if (auto it = _address_ptr_to_handle.find(&address);
        it == _address_ptr_to_handle.end())
    {
        const u32 handle = u32(_addresses_to_update.size());
        _addresses_to_update.push_back(&address);
        _address_ptr_to_handle[&address] = handle; 
    }
    
    // Release lock
}

void Hack::stop_auto_update(Address& address)
{
    if (address.type() == Address::Type::MANUAL) return;
    
    // Acquire lock

    if (auto it = _address_ptr_to_handle.find(&address);
        it != _address_ptr_to_handle.end())
    {
        const u32 handle = it->second;
        Address* last = _addresses_to_update.back();
        _addresses_to_update.pop_back();
        _addresses_to_update[handle] = last;
        _address_ptr_to_handle[last] = handle;
        _address_ptr_to_handle.erase(it->first);
    }

    // Release lock
}

void Hack::set_update_mask(u32 mask)
{
    _update_mask = mask;
}

void Hack::update()
{
    // Acquire lock
    
    for (auto* address: _addresses_to_update) { address->unload(); }

    const u32 mask = _update_mask;
    for (auto* address: _addresses_to_update) { address->update(mask); }
    
    // Release lock
}

void Hack::read_buffer(uptr ptr, Buffer& dst) const
{
    _process.read_memory(dst.data(), ptr, dst.size());
}

void Hack::write_buffer(uptr ptr, const Buffer& src) const
{
    _process.write_memory(ptr, src.data(), src.size());
}

uptr Hack::read_ptr(uptr ptr) const
{
    uptr v{};
    _process.read_memory(&v, ptr, _process.get_ptr_size());
    return v;
}

void Hack::write_ptr(uptr ptr, uptr v) const
{
	_process.write_memory(ptr, &v, _process.get_ptr_size());
}

string Hack::read_string(uptr ptr, usize size) const
{
    string s{};
    s.resize(size);
    _process.read_memory(s.data(), ptr, size);
    return s;
}

void Hack::write_string(uptr ptr, const string& v) const
{
	_process.write_memory(ptr, v.c_str(), v.size());
}

//endregion

//region Hack::Scan

Hack::Scan::Scan(u64 type_hash, const u8* data, usize value_size, uptr begin, usize size, usize max_results, bool read, bool write, bool execute, bool regex, bool threaded):
    begin{begin},
    size{size},
    value_size{value_size},
    max_results{max_results},
    type_hash{type_hash},
    read{read},
    write{write},
    execute{execute},
    regex{regex},
    threaded{threaded}
{
    PGH_ASSERT(read || write || execute, "To perform a scan, one of (read, write, execute) must be set to 'True'");

    if (value_size > BUFFER_SIZE) {
        ptr = (u8*)malloc(value_size);
        memset(ptr, 0, value_size);
    }
    else {
        memcpy(buffer, data, value_size);
    }
}

Hack::Scan::Scan(const string& data, uptr begin, usize size, usize max_results, bool read, bool write, bool execute, bool regex, bool threaded):
    Scan{typeid(string).hash_code(), (const u8*)data.c_str(), data.size(), begin, size, max_results, read, write, execute, regex, threaded}
{}

Hack::Scan::~Scan()
{
    if (ptr) {
        free(ptr);
    }
}

const u8* Hack::Scan::data() const
{
    return ptr ? ptr : buffer;
}

const u64 Hack::Scan::type_id() const
{
    return type_hash;
}

void Hack::Scan::set_value(u64 type_hash, const u8* data, usize value_size)
{
    PGH_ASSERT(type_hash == this->type_hash, "Cannot change the value type of a MemoryScan");

    if (value_size > BUFFER_SIZE) {
        memcpy(ptr, data, value_size);
    }
    else {
        memcpy(buffer, data, value_size);
    }
    this->value_size = value_size;
}

void Hack::Scan::set_value(const string& data)
{
    set_value(typeid(string).hash_code(), (const u8*)data.c_str(), data.size());
}

//endregion


template<typename T>
T& read(std::ifstream& stream, T& value)
{
    stream.read((char*)&value, sizeof(T));
    return value;
}

template<typename T>
void write(std::ofstream& stream, const T& value)
{
    stream.write((const char*)&value, sizeof(T));
}

template <class T>
static inline void hash_combine(usize& seed, const T& v)
{
    seed ^= std::hash<T>()(v) + 0x9e3779b9 + (seed<<6) + (seed>>2);
}

template<typename T>
static inline u32 bit_count(const T& value)
{
    u32 count = 0;
    T v = value;
    while (v) {
        v >>= 1;
        ++count;
    }
    return count;
}

//region Cheat Engine

struct CheatEnginePointerScan 
{
    using Settings = Hack::CE::Settings;

    // Regular data
    u8 magic{};
    u8 version{};
    u32 module_count{};
    u32 max_level{};
    u32 result_entry_size{};
    u8 did_base_range_scan{};
    u64 original_base_scan_range{};
    std::vector<string> module_names{};
    
    // Compressed scan data
    u32 mask_module_index{};
    u32 mask_level{};
    u32 mask_offset{};
    u8 is_compressed{};
    u8 is_aligned{};
    u8 max_bit_count_module_index{};
    u8 max_bit_count_module_offset{};
    u8 max_bit_count_level{};
    u8 max_bit_count_offset{32 - 2}; // The default max offset for uncompressed files is UINT32_MAX (4 byes)
    u8 ends_with_offset_count{};
    u32 ends_with_offset[16]{};

    // Results
    struct Result {
        u32 module_index0{};
        u32 module_offset{};
        u32 module_index1{};
        u32 offset_count{};
        u32 offsets[16]{};
    };
    std::vector<Result> results;

    static constexpr usize MIN_RESULTS_PER_FILE = 256;

    // Result size
    u32 calculate_result_entry_size() const 
    {
        if (is_compressed) {
            u32 s = max_bit_count_module_offset + max_bit_count_module_index + max_bit_count_level 
                    + max_bit_count_offset * (max_level - ends_with_offset_count);
            return (s + 7) / 8;
        }
        else {
            return 16 + (4 * max_level);
        }
    }

    // Load from file
    void load(const string& path, bool threaded)
    {
        read_modules(path);
        read_all_results(path, threaded);
    }

    void read_modules(const string& path)
    {
        std::ifstream input{path, std::ios::binary};

        // Read header
        read(input, magic);
        read(input, version);

        PGH_ASSERT(magic == 0xCE, "Not a cheat engine pointer scan file");
        PGH_ASSERT(version >= 2, "Invalid Version of Cheat Engine used to create this pointer scan file");
        
        read(input, module_count);
        module_names.resize(module_count);

        // Read module names
        u64 random_number_after_module{};
        for (u32 i = 0; i < module_count; ++i) {
            // Read name size
            u32 name_size{};
            read(input, name_size);
            // Read name
            module_names[i].resize(name_size);
            input.read(module_names[i].data(), name_size);
            // Read stupid 8 bytes after
            read(input, random_number_after_module);
        }

        // Read extra info
        read(input, max_level);
        read(input, is_compressed);
        
        // Read compressed info
        if (is_compressed) {
            read(input, is_aligned);
            read(input, max_bit_count_module_index);
            read(input, max_bit_count_module_offset);
            read(input, max_bit_count_level);
            read(input, max_bit_count_offset);
            read(input, ends_with_offset_count);
            for (u32 i = 0; i < ends_with_offset_count; ++i) {
                read(input, ends_with_offset[i]);
            }
        }
        
        // Read base scan range info
        read(input, did_base_range_scan);
        if (did_base_range_scan) {
            read(input, original_base_scan_range);
        }
        input.close();

        // Calculate size and masks
        result_entry_size = calculate_result_entry_size();
        if (is_compressed) {
            for (u32 i = 0; i < max_bit_count_module_index; ++i)    mask_module_index   = (mask_module_index << 1) ^ 1;
            for (u32 i = 0; i < max_bit_count_level; ++i)           mask_level          = (mask_level << 1) ^ 1;
            for (u32 i = 0; i < max_bit_count_offset; ++i)          mask_offset         = (mask_offset << 1) ^ 1;
        }
    }

    void read_results(const string& path, std::vector<Result>& rs) const
    {
        const usize size = std::filesystem::file_size(path);
        
        std::ifstream input{path, std::ios::binary};

        usize file_offset = 0;
        
        if (is_compressed) {
            while (file_offset < size) { 
                auto& result = rs.emplace_back();
                
                char buffer[256]{};
                input.read(buffer, result_entry_size);
                
                // Decode module offset
                if (max_bit_count_module_offset == 32)  result.module_offset = *((u32*)buffer);
                else                                    result.module_offset = u32(*((u64*)buffer));
                
                // Decode module index
                u32 bit = max_bit_count_module_offset;
                result.module_index0 = *((u32*)&buffer[bit >> 3]) & mask_module_index;            
                result.module_index1 = result.module_index0;
                bit += max_bit_count_module_index;

                // Decode offset count
                result.offset_count = ((*((u32*)&buffer[bit >> 3])) >> (bit & 7)) & mask_level;
                result.offset_count += ends_with_offset_count;
                bit += max_bit_count_level;
                
                // Decode offsets
                for (u32 i = 0; i < ends_with_offset_count; ++i) result.offsets[i] = ends_with_offset[i];

                for (u32 i = ends_with_offset_count; i < result.offset_count; ++i) {
                    u32 temp{};
                    u32 pos = bit >> 3;
                    memcpy(&temp, buffer + pos, std::min<u32>(result_entry_size - pos, 4u));
                    result.offsets[i] = (temp >> (bit & 7)) & mask_offset;
                    if (is_aligned) result.offsets[i] <<= 2;
                    bit += max_bit_count_offset;
                }

                file_offset += result_entry_size; 
            }
        }
        else {
            u32 off[16]{};
            while (file_offset < size) { 
                auto& result = rs.emplace_back();
                input.read((char*)&result, 16);
                input.read((char*)off, max_level * sizeof(u32));
                memcpy(result.offsets, off, result.offset_count * sizeof(u32));
                file_offset += result_entry_size; 
            }
        }

        input.close();
    }

    void read_all_results(const string& path, bool threaded)
    {
        auto prefix = path + ".results.";
        u32 index = 0;

        if (!threaded) {
            while(true) {
                auto result_path = prefix + std::to_string(index++);
                if (!std::filesystem::exists(result_path)) return;
                read_results(result_path, results);
            }
        }
        else {
            while (std::filesystem::exists(prefix + std::to_string(index++))) {}
            index -= 1;

            if (index == 1) {
                read_results(prefix + "0", results);
                return;
            }

            const usize n_threads = std::min<usize>(std::thread::hardware_concurrency(), index);
            const usize files_per_thread = 1 + (usize(index - 1) / n_threads);
            
            std::vector<std::thread> threads;
            std::vector<std::vector<Result>> all_results{};
            all_results.resize(n_threads);
            threads.resize(n_threads);
            
            for (usize i = 0; i < n_threads; ++i) {
                threads[i] = std::thread([this, &prefix, files_per_thread](usize i, std::vector<Result>* rs){
                    for (usize o = 0; o < files_per_thread; ++o) {
                        auto result_path = prefix + std::to_string(i * files_per_thread + o);
                        if (!std::filesystem::exists(result_path)) break;
                        read_results(result_path, *rs);
                    }
                }, i, &all_results[i]);
            }

            for (auto& thread: threads) {
                thread.join();
            }

            usize total_size = 0;
            for (const auto& r: all_results) { total_size += r.size(); }
            results.reserve(total_size);
            for (const auto& r: all_results) { results.insert(results.end(), r.begin(), r.end()); }
        }
    }

    // Save to file
    void save(const string& path, bool single_file) const
    {
        write_modules(path);
        write_all_results(path, single_file);
    }

    void write_modules(const string& path) const
    {
        std::ofstream output{path, std::ios::binary};
        
        // Write header
        write(output, magic);
        write(output, version);

        write(output, module_count);

        // Write module names
        u64 random_number_after_module{};
        for (u32 i = 0; i < module_count; ++i) {
            // Write name size
            write(output, u32(module_names[i].size()));
            // Write name
            output.write(module_names[i].data(), module_names[i].size());
            // Write stupid 8 bytes after
            write(output, random_number_after_module);
        }

        // Write extra info
        write(output, max_level);
        write(output, is_compressed);
        
        // Write compressed info
        if (is_compressed) {
            write(output, is_aligned);
            write(output, max_bit_count_module_index);
            write(output, max_bit_count_module_offset);
            write(output, max_bit_count_level);
            write(output, max_bit_count_offset);
            write(output, ends_with_offset_count);
            for (u32 i = 0; i < ends_with_offset_count; ++i) {
                write(output, ends_with_offset[i]);
            }
        }
        
        // Write base scan range info
        write(output, did_base_range_scan);
        if (did_base_range_scan) {
            write(output, original_base_scan_range);
        }
        
        output.close();
    }

    void write_results(const string& path, const Result* begin, const Result* end) const
    {
        std::ofstream output{path, std::ios::binary};
        
        if (is_compressed) {
            char buffer[256]{};
            for (const auto* it = begin; it != end; ++it) {
                const auto& result = *it;
                memset(buffer, 0, result_entry_size);

                // Encode module offset
                if (max_bit_count_module_offset == 32)  *((u32*)buffer) = result.module_offset;
                else                                    *((u64*)buffer) = result.module_offset;

                // Encode module index
                u32 bit = max_bit_count_module_offset;
                *((u32*)&buffer[bit >> 3]) |= result.module_index0;
                bit += max_bit_count_module_index;

                // Encode offset count
                *((u32*)&buffer[bit >> 3]) |= (result.offset_count - ends_with_offset_count) << (bit & 7);
                bit += max_bit_count_level;
                
                // Encode offsets
                for (u32 i = ends_with_offset_count; i < result.offset_count; ++i) {
                    buffer[bit >> 3] |= (result.offsets[i] >> (is_aligned ? 2 : 0)) << (bit & 7);
                    bit += max_bit_count_offset;
                }

                output.write(buffer, result_entry_size);
            }
        }
        else {
            u32 off[16]{};
            for (const auto* it = begin; it != end; ++it) {
                const auto& result = *it;
                memset(off, 0xCE, 16 * sizeof(u32));
                memcpy(off, result.offsets, result.offset_count * sizeof(u32));
                output.write((const char*)&result, 16);
                output.write((const char*)off, max_level);
            }
        }

        output.close();
    }

    void write_all_results(const string& path, bool single_file) const
    {
        const usize max_file_index = single_file ? 1 : (1 + (results.size() / MIN_RESULTS_PER_FILE));
        
        // Do not write in parallel if there is not more than 1 file to write to
        if (single_file || max_file_index == 1) {
            write_results(path + ".results.0", results.data(), results.data() + results.size());
        }
        // Write in parallel if requested and more than one file will be written to
        else {
            auto prefix = path + ".results.";
            const usize results_per_file = results.size() / max_file_index;
        
            std::vector<std::thread> threads;
            threads.resize(max_file_index);
            for (usize i = 0; i < max_file_index; ++i) {
                threads[i] = std::thread([this, &prefix, results_per_file](usize i){
                    write_results(prefix + std::to_string(i), 
                        results.data() + (i * results_per_file), 
                        results.data() + std::min<usize>(results.size(), ((i + 1) * results_per_file)));
                }, i);
            }
            for (auto& thread: threads) {
                thread.join();
            }
        }
    }

    // Address -> Cheat engine data
    void load_addresses(const Hack::CE::AddressPtrs& addresses)
    {
        // Extract modules from static addresses
        std::unordered_map<string, u32> existing{};
        std::unordered_map<const Address*, u32> address_to_module_index{};

        for (const auto* address: addresses) {
            if (address->type() == Address::Type::STATIC) 
            {
                if (auto it = existing.find(address->module_name());
                    it != existing.end())
                {
                    address_to_module_index.emplace(address, it->second);   
                }
                else {
                    u32 module_index = u32(module_names.size());
                    module_names.push_back(address->module_name());
                    ++module_count;
                    existing.emplace(address->module_name(), module_index);
                    address_to_module_index.emplace(address, module_index);
                }
            }
        }
        max_bit_count_module_index = bit_count(module_count);

        // Convert addresses to cheat engine pointer scan results
        results.reserve(addresses.size());
        for (const auto* address: addresses) {
            auto& result = results.emplace_back();
            if (address->type() == Address::Type::STATIC) {
                result.module_index0 = address_to_module_index.at(address);
                result.module_index1 = result.module_index0;
                result.module_offset = u32(address->module_offset());
            }
            else {
                PGH_ASSERT(address->offsets().size() < (sizeof(Result::offsets) / sizeof(u32)), "Too many offsets in CheatEngine PointerScan Result");
                const auto& parent = address->parent();
                PGH_ASSERT(parent.type() == Address::Type::STATIC, "Dynamic address parent must be static address");
                PGH_ASSERT(address_to_module_index.count(&parent), "Static parent address does not have a corresponding module");
                result.module_index0 = address_to_module_index.at(&parent);
                result.module_index1 = result.module_index0;
                result.module_offset = u32(parent.module_offset());
                result.offset_count = u32(address->offsets().size());
                memcpy(result.offsets, address->offsets().data(), result.offset_count);
            }
        }
    }

    void save_addresses(Hack& hack, Hack::CE::Addresses& addresses) const
    {
        std::unordered_map<usize, u32> existing{};

        for (const auto& result: results) {
            usize hash = 0;
            hash_combine(hash, result.module_index0);
            hash_combine(hash, result.module_offset);

            if (auto it = existing.find(hash); it != existing.end()) {
                addresses.emplace_back(std::move(Address::CreateDynamic(addresses[it->second], result.offsets, result.offset_count, true)));
            }
            else {
                existing.emplace(hash, u32(addresses.size()));
                addresses.emplace_back(std::move(Address::Static(hack, module_names[result.module_index0], result.module_offset)));
            }
        }
    }

    // Settings
    void load_settings(const Settings& settings)
    {
        max_level = settings.max_level;
        is_compressed = settings.is_compressed;
        
        if (settings.is_compressed) {
            is_aligned = settings.is_aligned;

            max_bit_count_module_offset = 32;
            // max_bit_count_module_index; <-- this is calculated in 'load_addresses'
            max_bit_count_level = bit_count(max_level);
            max_bit_count_offset = bit_count(settings.max_offset >> 2);
            
            ends_with_offset_count = u32(settings.ends_with_offsets.size());
            memcpy(ends_with_offset, settings.ends_with_offsets.data(), settings.ends_with_offsets.size() * sizeof(u32));
        }
        
        // These values are always the same so they can be hard-coded
        magic = 0xce;
        version = 2;

        // This is only required for scanning in Cheat Engine, 
        // not for reading/writing files, so it can be ignored
        did_base_range_scan = 0;
        original_base_scan_range = 0;

        // This value must be calculated after all of the bit sizes are calculated
        result_entry_size = calculate_result_entry_size();
    }

    void save_settings(Settings& settings) const 
    {
        settings.max_level = max_level;
        settings.max_offset = u32(u64((1ull << (max_bit_count_offset + 2))) - 1ull);
        settings.is_compressed = bool(is_compressed);
        settings.is_aligned = bool(is_aligned);
        for (u32 i = 0; i < ends_with_offset_count; ++i) {
            settings.ends_with_offsets.push_back(ends_with_offset[i]);
        }
    }
};

Hack::CE::PointerScanLoad Hack::cheat_engine_load_pointer_scan_file(const string& path, bool threaded)
{
    CE::Addresses addresses;
    
    CheatEnginePointerScan scan{};
    scan.load(path, threaded);
    scan.save_addresses(*this, addresses);
    
    CE::Settings settings{};
    scan.save_settings(settings);

    return CE::PointerScanLoad{std::move(addresses), settings};
}

void Hack::cheat_engine_save_pointer_scan_file(const string& path, const CE::AddressPtrs& addresses, const CE::Settings& settings, bool single_file)
{
    CheatEnginePointerScan scan{};
    scan.load_settings(settings);
    scan.load_addresses(addresses);
    scan.save(path, single_file);
}

//endregion

}
