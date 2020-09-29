#include "Proc.h"

#include <thread>
#include <iostream>

// MARK: Helpers

#ifdef _MSC_VER

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


WindowsProcessAPI::~WindowsProcessAPI()
{
	if (handle) { CloseHandle(handle); }
}

bool WindowsProcessAPI::is_attached() const
{
	return (handle != nullptr) && (WaitForSingleObject(handle, 0) == WAIT_OBJECT_0 ? false : true);
}

bool WindowsProcessAPI::is_64_bit() const
{
	int b32_on_b64{ false };
	IsWow64Process(handle, &b32_on_b64);
	return !b32_on_b64;
}

void WindowsProcessAPI::attach(const char* process_name)
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
		std::string msg = std::string{ "Could not find process " } + std::string{ process_name };
		throw std::exception{ msg.c_str() };
	}

	handle = OpenProcess(PROCESS_ALL_ACCESS, NULL, id);
}

void WindowsProcessAPI::get_modules(ModuleMap& modules) const
{
	HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, id);
	if (hSnap != INVALID_HANDLE_VALUE) {
		MODULEENTRY32 modEntry;
		modEntry.dwSize = sizeof(modEntry);
		if (Module32First(hSnap, &modEntry)) {
			do {
				modules.emplace(
					(const char*)modEntry.szModule, 
					std::tuple<Ptr, size_t>{ (Ptr)modEntry.modBaseAddr, (size_t)modEntry.modBaseSize }
				);
			} while (Module32Next(hSnap, &modEntry));
		}
	}
	CloseHandle(hSnap);
}

bool WindowsProcessAPI::read_memory(void* dst, const void* src, size_t size) const
{
	return ReadProcessMemory(handle, src, dst, size, nullptr);
}

bool WindowsProcessAPI::write_memory(void* dst, const void* src, size_t size) const
{
	return WriteProcessMemory(handle, dst, src, size, nullptr);
}

Ptr WindowsProcessAPI::follow_ptr_path(Ptr ptr, const PtrPath& offsets, size_t ptr_size, bool read_first) const
{
	Ptr addr = ptr;
	bool did_read_once = false;
	for (const auto& off : offsets) {
		if (read_first || did_read_once) {
			read_memory(&addr, (LPCVOID)addr, ptr_size);
		}
		addr += off;
		did_read_once = true;
	}
	return addr;
}

void WindowsProcessAPI::iter_regions(Ptr begin, size_t size, std::function<bool(Ptr, size_t, uint8_t*)>&& callback, size_t block_size) const
{
	std::vector<uint8_t> data;
	data.resize(block_size);

	Ptr current{begin}, region_begin{};
	size_t region{}, region_size{}, step{};
	MEMORY_BASIC_INFORMATION mbi{};

	while (current < begin + size) {
		region = VirtualQueryEx(handle, (LPCVOID)current, &mbi, sizeof(mbi));

		if (region && mbi.State != MEM_FREE) {
			region_begin = reinterpret_cast<Ptr>(mbi.BaseAddress);
			current = region_begin;
			region_size = mbi.RegionSize;
			
			Ptr region_end = region_begin + region_size;

			while (current < region_end) {
				step = min(region_size, min(region_end - current, block_size));
				read_memory(data.data(), (LPCVOID)current, step);
				
				if (callback(current, step, data.data())) {
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

void WindowsProcessAPI::with_full_access(Ptr ptr, size_t size, std::function<void(Ptr, size_t)>&& callback) const
{
	DWORD protect, old_protect;
	VirtualProtectEx(handle, (LPVOID)ptr, size, PAGE_EXECUTE_READWRITE, &old_protect);
	callback(ptr, size);
	VirtualProtectEx(handle, (LPVOID)ptr, size, old_protect, &protect);
}


#else

#endif



// MARK: Process

uint32_t Process::pid() const
{
	return api.pid();
}

bool Process::is_attached() const
{
	return api.is_attached();
}

bool Process::attach(const std::string& process_name)
{
	name = process_name;
	modules.clear();
	api.attach(process_name.c_str());
	ptr_t = api.is_64_bit() ? PointerType::BIT64 : PointerType::BIT32;
	api.get_modules(modules);
	return api.is_attached();
}

Ptr Process::get_module_base_address(const std::string& module_name) const
{
	auto it = modules.find(module_name);
	if (it == modules.end()) {
		std::string msg = std::string{ "Could not find module " } + module_name;
		throw std::exception{ msg.c_str() };
	}
	return std::get<0>(it->second);
}

bool Process::read_memory(void* dst, Ptr src, size_t size) const
{
	return api.read_memory(dst, (void*)normalize_ptr(src), size);
}

bool Process::write_memory(Ptr dst, const void* src, size_t size) const
{
	return api.write_memory((void*)normalize_ptr(dst), src, size);
}

Ptr Process::follow_ptr_path(Ptr start, const PtrPath& offsets, bool read_first) const
{
	return api.follow_ptr_path(start, offsets, ptr_t == BIT32 ? 4u : 8u, read_first);
}

void Process::iter_regions(Ptr begin, size_t size, std::function<bool(Ptr, size_t, uint8_t*)>&& callback, size_t block_size) const
{
	return api.iter_regions(begin, size, std::forward<decltype(callback)>(callback), block_size);
}

void Process::with_full_access(Ptr ptr, size_t size, std::function<void(Ptr, size_t)>&& callback) const
{
	api.with_full_access(ptr, size, std::forward<decltype(callback)>(callback));
}


Ptr Process::normalize_ptr(Ptr ptr) const 
{ 
	return (ptr_t == BIT32 ? (ptr & UINT32_MAX) : ptr); 
}
