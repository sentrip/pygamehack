#include "Process.h"

//region Platform APIs

#ifdef _MSC_VER

#include <cassert>
#include <exception>

#include <windows.h>
#include <process.h>
#include <TlHelp32.h>

#include <wingdi.h>

#include <stdlib.h>
#include <stdio.h>
#include <tchar.h>
#include <wchar.h>

#include <locale>
#include <codecvt>

#endif

namespace pygamehack {

#ifdef _MSC_VER

#define API_CLASS WindowsProcessAPI

// TODO: WindowsProcessAPI safety asserts/checks
class WindowsProcessAPI {
	uint32_t id{ 0 };
	void* handle{ nullptr };
public:
    //region Basic

    WindowsProcessAPI() = default;

	~WindowsProcessAPI() { detach(); }

	uint32_t pid() const 
    { 
        return id; 
    }

	bool is_attached() const
    {
	    return (handle != nullptr) && (WaitForSingleObject(handle, 0) == WAIT_OBJECT_0 ? false : true);
    }

	bool is_64_bit() const
    {
        int b32_on_b64{ false };
        IsWow64Process(handle, &b32_on_b64);
        return !b32_on_b64;
    }

    static void kill(u32 id)
    {
        HANDLE hProcess = OpenProcess(PROCESS_TERMINATE, 0, (DWORD) id);
        if (hProcess != NULL)
        {
            TerminateProcess(hProcess, 9);
            CloseHandle(hProcess);
        }
    }

    static u64 created_at(u32 id)
    {
        u64 time = 0;
        HANDLE hProcess = OpenProcess(PROCESS_QUERY_INFORMATION, 0, (DWORD) id);
        if (hProcess != NULL)
        {
            FILETIME createTime, exitTime, kernelTime, userTime;
            if (GetProcessTimes(hProcess, &createTime, &exitTime, &kernelTime, &userTime)) {
                time |= u64(createTime.dwLowDateTime);
                time |= (u64(createTime.dwHighDateTime) << 32);
            }
            CloseHandle(hProcess);
        }
        return time;
    }

    static u64 entry_point(const string& executable_name)
    {
        HANDLE file = NULL;
        DWORD fileSize = NULL;
        DWORD bytesRead = NULL;
        LPVOID fileData = NULL;

        // open file
        file = CreateFileA(executable_name.c_str(), GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
        if (file == INVALID_HANDLE_VALUE) return 0;
        
        // allocate heap
        fileSize = GetFileSize(file, NULL);
        fileData = HeapAlloc(GetProcessHeap(), 0, fileSize);
        
        // read file bytes to memory
        ReadFile(file, fileData, fileSize, &bytesRead, NULL);

        // read headers
        PIMAGE_DOS_HEADER dosHeader = (PIMAGE_DOS_HEADER)fileData;
        PIMAGE_NT_HEADERS imageNTHeaders = (PIMAGE_NT_HEADERS)(u64(fileData) + dosHeader->e_lfanew);
        u64 entry = imageNTHeaders->OptionalHeader.AddressOfEntryPoint;

        // cleanup
        HeapFree(GetProcessHeap(), 0, fileData);
        CloseHandle(file);

        return entry;
    }

    //endregion

    //region Memory

	bool read_memory(void* dst, const void* src, usize size) const
    {
        return ReadProcessMemory(handle, src, dst, size, nullptr);
    }

	bool write_memory(void* dst, const void* src, usize size) const
    {
        return WriteProcessMemory(handle, dst, src, size, nullptr);
    }
    
	Memory::Protect virtual_protect(uptr ptr, usize size, Memory::Protect protect) const
    {
        DWORD old_protect;
        VirtualProtectEx(handle, (LPVOID)ptr, size, get_platform_protect(protect), &old_protect);
        return get_pygamehack_protect(old_protect);
    }

	uptr follow_ptr_path(uptr ptr, const uptr_path& offsets, usize ptr_size) const
    {
        uptr addr = ptr;
        usize size = offsets.size();
        for (usize i = 0; i < size; ++i) {
            if (i > 0) read_memory(&addr, (LPCVOID)addr, ptr_size);
            addr += offsets[i];
        }
        return addr;
    }

    //endregion

    //region Attach/Detach

	void attach(const char* process_name)
    {
        if (handle) {
            CloseHandle(handle);
        }

        bool did_find = false;
        DWORD procId = 0;
        HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);

        if (hSnap != INVALID_HANDLE_VALUE) {
            PROCESSENTRY32 procEntry;
            procEntry.dwSize = sizeof(procEntry);

            if (Process32First(hSnap, &procEntry)) {
                do {
                    if (!strcmp((const char*)procEntry.szExeFile, process_name)) {
                        id = procEntry.th32ProcessID;
                        did_find = true;
                        break;
                    }

                } while (Process32Next(hSnap, &procEntry));
            }
        }
        CloseHandle(hSnap);

        if (!did_find) {
            string msg = string{ "Could not find process " } + string{ process_name };
            throw std::exception{ msg.c_str() };
        }

        handle = OpenProcess(PROCESS_ALL_ACCESS, NULL, id);

        if (!handle) {
            id = 0;
            string msg = string{ "Failed to open process " } + string{ process_name };
            throw std::exception{ msg.c_str() };
        }
    }

	void attach(u32 pid) {
	    id = pid;
        handle = OpenProcess(PROCESS_ALL_ACCESS, NULL, id);
        if (!handle) {
            id = 0;
            string msg = string{ "Failed to open process " } + std::to_string(pid);
            throw std::exception{ msg.c_str() };
        }
    }

    void detach()
    {
        if (!handle) return;
        CloseHandle(handle);
        handle = nullptr;
        id = 0;
    }

    //endregion

    //region OS API Iteration

	void get_modules(module_map& modules) const
    {
        HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, id);
        if (hSnap != INVALID_HANDLE_VALUE) {
            MODULEENTRY32 modEntry;
            modEntry.dwSize = sizeof(modEntry);
            if (Module32First(hSnap, &modEntry)) {
                do {
                    modules.emplace(
                        (const char*)modEntry.szModule, 
                        std::tuple<uptr, usize>{ (uptr)modEntry.modBaseAddr, (usize)modEntry.modBaseSize }
                    );
                } while (Module32Next(hSnap, &modEntry));
            }
        }
        CloseHandle(hSnap);
    }

	void iter_regions(uptr begin, usize size, Process::iter_region_callback&& callback, Memory::Protect protect, bool read, usize block_size) const
    {
        PGH_ASSERT(block_size > 0, "Block size cannot be 0");

        std::vector<u8> data;
        if (read) data.resize(block_size);

        uptr current{begin}, region_begin{};
        usize region{}, region_size{}, step{};
        MEMORY_BASIC_INFORMATION mbi{};

        while (current < begin + size) {
            region = VirtualQueryEx(handle, (LPCVOID)current, &mbi, sizeof(mbi));

            if (region && mbi.State != MEM_FREE) {
                region_begin = reinterpret_cast<uptr>(mbi.BaseAddress);
                current = region_begin;
                region_size = mbi.RegionSize;
                
                uptr region_end = region_begin + region_size;

                while (current < region_end) {
                    step = min(region_size, min(region_end - current, block_size));
                    
                    Memory::Protect old_protect;
                    if (protect != Memory::Protect::NONE) {
                        old_protect = virtual_protect(current, step, protect);
                    }

                    if (read) {
                        if (step > data.size()) data.resize(step);
                        read_memory(data.data(), (LPCVOID)current, step);
                    }
                    
                    bool done = false;
                    if (callback(current, step, data.data())) {
                        done = true;
                    }

                    if (protect != Memory::Protect::NONE) {
                        virtual_protect(current, step, old_protect);
                    }
                    
                    if (done) {
                        return;
                    }

                    current += step;
                }
            }
            else if (region && mbi.State == MEM_FREE) {
                current += mbi.RegionSize;
            }
            else {
                current += 4096;
            }
        }
    }

    static void iter(Process::iter_callback&& callback)
    {
        // take a snapshot of processes
        DWORD dwFlags = TH32CS_SNAPPROCESS;
        HANDLE hSnapshot = ::CreateToolhelp32Snapshot(dwFlags, 0);
        if (INVALID_HANDLE_VALUE == hSnapshot)
        {
            ::GetLastError();
            return;
        }
        PROCESSENTRY32 processEntry = {0};
        processEntry.dwSize = sizeof(PROCESSENTRY32);
        // get info for each process in the snapshot
        if (::Process32First(hSnapshot, &processEntry))
        {
            do
            {
                ProcessInfo info{processEntry.th32ProcessID, processEntry.th32ParentProcessID, processEntry.dwSize, processEntry.cntThreads};
                info.name = (const char*)processEntry.szExeFile;
                if (callback(info)) {
                    break;
                }
            } while (::Process32Next(hSnapshot, &processEntry));
        }
        else
        {
            ::GetLastError();
        }
        ::CloseHandle(hSnapshot);
    }

    //endregion

    //region Protect conversion

    static u32 get_platform_protect(Memory::Protect protect)
    {
        u32 native{};
        if (u32(protect) & u32(Memory::Protect::NO_ACCESS)) { native |= PAGE_NOACCESS; }
        if (u32(protect) & u32(Memory::Protect::READ_ONLY)) { native |= PAGE_READONLY; }
        if (u32(protect) & u32(Memory::Protect::READ_WRITE)) { native |= PAGE_READWRITE; }
        if (u32(protect) & u32(Memory::Protect::WRITE_COPY)) { native |= PAGE_WRITECOPY; }
        if (u32(protect) & u32(Memory::Protect::EXECUTE)) { native |= PAGE_EXECUTE; }
        if (u32(protect) & u32(Memory::Protect::EXECUTE_READ)) { native |= PAGE_EXECUTE_READ; }
        if (u32(protect) & u32(Memory::Protect::EXECUTE_READ_WRITE)) { native |= PAGE_EXECUTE_READWRITE; }
        if (u32(protect) & u32(Memory::Protect::EXECUTE_WRITE_COPY)) { native |= PAGE_EXECUTE_WRITECOPY; }
        if (u32(protect) & u32(Memory::Protect::GUARD)) { native |= PAGE_GUARD; }
        if (u32(protect) & u32(Memory::Protect::NO_CACHE)) { native |= PAGE_NOCACHE; }
        if (u32(protect) & u32(Memory::Protect::WRITE_COMBINE)) { native |= PAGE_WRITECOMBINE; }
        return native;
    }

    static Memory::Protect get_pygamehack_protect(u32 protect)
    {
        u32 py_protect{};
        if(protect & PAGE_NOACCESS) { py_protect |= u32(Memory::Protect::NO_ACCESS); }
        if(protect & PAGE_READONLY) { py_protect |= u32(Memory::Protect::READ_ONLY); }
        if(protect & PAGE_READWRITE) { py_protect |= u32(Memory::Protect::READ_WRITE); }
        if(protect & PAGE_WRITECOPY) { py_protect |= u32(Memory::Protect::WRITE_COPY); }
        if(protect & PAGE_EXECUTE) { py_protect |= u32(Memory::Protect::EXECUTE); }
        if(protect & PAGE_EXECUTE_READ) { py_protect |= u32(Memory::Protect::EXECUTE_READ); }
        if(protect & PAGE_EXECUTE_READWRITE) { py_protect |= u32(Memory::Protect::EXECUTE_READ_WRITE); }
        if(protect & PAGE_EXECUTE_WRITECOPY) { py_protect |= u32(Memory::Protect::EXECUTE_WRITE_COPY); }
        if(protect & PAGE_GUARD) { py_protect |= u32(Memory::Protect::GUARD); }
        if(protect & PAGE_NOCACHE) { py_protect |= u32(Memory::Protect::NO_CACHE); }
        if(protect & PAGE_WRITECOMBINE) { py_protect |= u32(Memory::Protect::WRITE_COMBINE); }
        return Memory::Protect(py_protect);
    }

    //endregion
};

#else
#error "pygamehack is Windows-only at the moment"
#endif

#define API (*((API_CLASS*)&os_api_storage[0]))
#define API_VAR(v) (*((API_CLASS*)&v->os_api_storage[0]))

//endregion


//region Memory

Memory::Memory(const Process& process, uptr ptr, usize size, Protect protect):
    process{&process},
    ptr{ptr},
    size{size},
    protection{protect},
    modified{false}
{}

Memory::~Memory()
{
    if (modified) reset();
}

void Memory::protect()
{
    protection = API_VAR(process).virtual_protect(ptr, size, protection);
    modified = true;
}

void Memory::reset()
{
    protection = API_VAR(process).virtual_protect(ptr, size, protection);
    modified = false;
}

//endregion


//region Process

Process::~Process()
{
    API.~API_CLASS();
}

Process::Arch Process::arch() const
{
	return _arch;
}

u32 Process::pid() const
{
    return API.pid();
}

const module_map& Process::modules() const
{
    return _modules;
}

bool Process::is_attached() const
{

    return API.is_attached();
}

bool Process::attach(u32 process_id)
{
	_modules.clear();
	API.attach(process_id);
	_arch = API.is_64_bit() ? Arch::X64 : Arch::X86;
	API.get_modules(_modules);
	return API.is_attached();
}

bool Process::attach(const string& process_name)
{
	_modules.clear();
	API.attach(process_name.c_str());
	_arch = API.is_64_bit() ? Arch::X64 : Arch::X86;
	API.get_modules(_modules);
	return API.is_attached();
}

void Process::detach()
{
    API.detach();
}

u32 Process::get_ptr_size() const
{
    return _arch == Arch::X64 ? sizeof(u64) : sizeof(u32);
}

u64 Process::get_max_ptr() const
{
    return _arch == Arch::X86 ? u64(UINT32_MAX) : u64(UINT64_MAX);
}

uptr Process::get_base_address(const string& module_name) const
{
	auto it = _modules.find(module_name);
	if (it == _modules.end()) {
		string msg = string{ "Could not find module " } + module_name;
		throw std::exception{ msg.c_str() };
	}
	return std::get<0>(it->second);
}

bool Process::read_memory(void* dst, uptr src, usize size) const
{
	return API.read_memory(dst, (void*)normalize_ptr(src), size);
}

bool Process::write_memory(uptr dst, const void* src, usize size) const
{
	return API.write_memory((void*)normalize_ptr(dst), src, size);
}

uptr Process::find_char(i8 value, uptr begin, usize size) const
{
    i8 v;
    for (uptr p = begin; p < begin + size; ++p) {
		if (read_memory(&v, p, 1u) && v == value) 
            return p - begin;
	}
	return 0;
}

uptr Process::follow(uptr start, const uptr_path& offsets) const
{
	return API.follow_ptr_path(start, offsets, _arch == Arch::X86 ? 4u : 8u);
}

void Process::iter_regions(uptr begin, usize size, iter_region_callback&& callback, Memory::Protect prot, bool read, usize block_size) const
{
	return API.iter_regions(begin, size, std::forward<iter_region_callback>(callback), prot, read, block_size);
}

Memory Process::protect(uptr ptr, usize size, Memory::Protect prot) const
{
    return Memory{*this, ptr, size, prot};
}

void Process::iter(iter_callback&& callback) 
{
    API_CLASS::iter(std::forward<iter_callback>(callback));
}

void Process::kill(u32 id) 
{
    API_CLASS::kill(id);
}

u64 Process::created_at(u32 id)
{
    return API_CLASS::created_at(id);
}

u64 Process::entry_point(const string& executable_name)
{
    return API_CLASS::entry_point(executable_name);
}

uptr Process::normalize_ptr(uptr ptr) const 
{ 
	return (_arch == Arch::X86 ? (ptr & UINT32_MAX) : ptr); 
}

//endregion

}
