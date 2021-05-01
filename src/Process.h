
#ifndef PYGAMEHACK_PROCESS_H
#define PYGAMEHACK_PROCESS_H

#include "config.h"
#include <functional>
#include <tuple>
#include <vector>
#include <unordered_map>

namespace pygamehack {
    
class Process;
using uptr_path = std::vector<uptr>;
using module_map = std::unordered_map<string, std::tuple<uptr, usize>>;


class Memory {
public:
    enum class Protect {
        NONE = 0,
        NO_ACCESS = 1 << 0,
        READ_ONLY = 1 << 1,
        READ_WRITE = 1 << 2,
        WRITE_COPY = 1 << 3,
        EXECUTE = 1 << 4,
        EXECUTE_READ = 1 << 5,
        EXECUTE_READ_WRITE = 1 << 6,
        EXECUTE_WRITE_COPY = 1 << 7,
        GUARD = 1 << 8,
        NO_CACHE = 1 << 9,
        WRITE_COMBINE = 1 << 10
    };

    Memory() = default;
    Memory(const Process& process, uptr ptr, usize size, Protect protect);
    ~Memory();
    void protect();
    void reset();

private:
    const Process* process{};
    uptr  ptr{};
    usize size{};
    Protect protection{};
    bool  modified{};
};


struct ProcessInfo {
    u32 id{};
    u32 parent_id{};
    u32 size{};
    u32 thread_count{};
    string name{};
};


class Process {
public:
    enum class Arch { X86, X64, NONE };

    using iter_callback                 = std::function<bool(const ProcessInfo&)>;
    using iter_region_callback          = std::function<bool(uptr, usize, const u8*)>;

    Process() = default;
    ~Process();

    Arch arch() const;

	u32  pid() const;

    const module_map& modules() const;

	bool is_attached() const;

	bool attach(u32 process_id);
	bool attach(const string& process_name);

    void detach();

    u32  get_ptr_size() const;

    u64  get_max_ptr() const;

	uptr get_base_address(const string& module_name) const;

	bool read_memory(void* dst, uptr src, usize size) const;

	bool write_memory(uptr dst, const void* src, usize size) const;
	
    uptr find_char(i8 value, uptr begin, usize size) const;

	uptr follow(uptr start, const uptr_path& offsets) const;

	void iter_regions(uptr begin, usize size, iter_region_callback&& callback, Memory::Protect prot = Memory::Protect::NONE, bool read=true, usize block_size = 4096) const;
    
    Memory protect(uptr ptr, usize size, Memory::Protect prot = Memory::Protect::READ_WRITE) const;

    static void iter(iter_callback&& callback);

    static void kill(u32 id);

    static u64 created_at(u32 id);

    static u64 entry_point(const string& executable_name);

private:
    friend class Memory; // protect/reset

    uptr normalize_ptr(uptr ptr) const;

    u64 os_api_storage[4]{};
	module_map _modules{};
    Arch _arch{Arch::NONE};
};

}

#endif
