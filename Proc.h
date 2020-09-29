#pragma once

#include <functional>
#include <iterator>
#include <string>
#include <unordered_map>
#include <vector>

using Ptr = uintptr_t;
using PtrPath = std::vector<unsigned int>;
using ModuleMap = std::unordered_map<std::string, std::tuple<Ptr, size_t>>;
enum PointerType { BIT32, BIT64 };



class MacOSProcessAPI {
public:
	uint32_t pid() const { 0; }

	bool is_attached() const { return false; }

	bool is_64_bit() const { return true; }

	void attach(const char* process_name) {}

	void get_modules(ModuleMap& modules) const {}

	bool read_memory(void* dst, Ptr src, size_t size) const { return false; }

	bool write_memory(Ptr dst, const void* src, size_t size) const { return false; }

	Ptr follow_ptr_path(Ptr ptr, const PtrPath& offsets, size_t ptr_size, bool read_first) const { return 0; }

	void iter_regions(Ptr begin, size_t size, std::function<bool(Ptr, size_t, uint8_t*)>&& callback, size_t block_size) const {}

	void with_full_access(Ptr ptr, size_t size, std::function<void(Ptr, size_t)>&& callback) const {}
};

class WindowsProcessAPI {
	uint32_t id{ 0 };
	void* handle{ nullptr };
public:
	~WindowsProcessAPI();

	uint32_t pid() const { return id; }

	bool is_attached() const;

	bool is_64_bit() const;

	void attach(const char* process_name);

	void get_modules(ModuleMap& modules) const;

	bool read_memory(void* dst, const void* src, size_t size) const;

	bool write_memory(void* dst, const void* src, size_t size) const;

	Ptr follow_ptr_path(Ptr ptr, const PtrPath& offsets, size_t ptr_size, bool read_first) const;

	void iter_regions(Ptr begin, size_t size, std::function<bool(Ptr, size_t, uint8_t*)>&& callback, size_t block_size) const;

	void with_full_access(Ptr ptr, size_t size, std::function<void(Ptr, size_t)>&& callback) const;
};


class Process {

#ifdef _MSC_VER
	WindowsProcessAPI api;
#else
	MacOSProcessAPI api;
#endif

public:
	ModuleMap modules;
	PointerType ptr_t{ BIT64 };
	std::string name;
	
	Process() = default;

	uint32_t pid() const;

	bool is_attached() const;

	bool attach(const std::string& process_name);

	Ptr get_module_base_address(const std::string& module_name) const;

	bool read_memory(void* dst, Ptr src, size_t size) const;

	bool write_memory(Ptr dst, const void* src, size_t size) const;
	
	Ptr follow_ptr_path(Ptr start, const PtrPath& offsets, bool read_first) const;

	void iter_regions(Ptr begin, size_t size, std::function<bool(Ptr, size_t, uint8_t*)>&& callback, size_t block_size = 4096) const;

	void with_full_access(Ptr ptr, size_t size, std::function<void(Ptr, size_t)>&& callback) const;

private:
	Ptr normalize_ptr(Ptr ptr) const;
};


// A forward iterator that "flattens" a container of containers.  For example,
// a vector<vector<int>> containing { { 1, 2, 3 }, { 4, 5, 6 } } is iterated as
// a single range, { 1, 2, 3, 4, 5, 6 }.
template <typename OuterIterator>
class flattening_iterator
{
public:

    typedef OuterIterator                                outer_iterator;
    typedef typename OuterIterator::value_type::iterator inner_iterator;

    typedef std::forward_iterator_tag                iterator_category;
    typedef typename inner_iterator::value_type      value_type;
    typedef typename inner_iterator::difference_type difference_type;
    typedef typename inner_iterator::pointer         pointer;
    typedef typename inner_iterator::reference       reference;

    flattening_iterator() { }
    flattening_iterator(outer_iterator it) : outer_it_(it), outer_end_(it) { }
    flattening_iterator(outer_iterator it, outer_iterator end)
        : outer_it_(it),
        outer_end_(end)
    {
        if (outer_it_ == outer_end_) { return; }

        inner_it_ = outer_it_->begin();
        advance_past_empty_inner_containers();
    }

    reference operator*()  const { return *inner_it_; }
    pointer   operator->() const { return &*inner_it_; }

    flattening_iterator& operator++()
    {
        ++inner_it_;
        if (inner_it_ == outer_it_->end())
            advance_past_empty_inner_containers();
        return *this;
    }

    flattening_iterator operator++(int)
    {
        flattening_iterator it(*this);
        ++* this;
        return it;
    }

    friend bool operator==(const flattening_iterator& a,
        const flattening_iterator& b)
    {
        if (a.outer_it_ != b.outer_it_)
            return false;

        if (a.outer_it_ != a.outer_end_ &&
            b.outer_it_ != b.outer_end_ &&
            a.inner_it_ != b.inner_it_)
            return false;

        return true;
    }

    friend bool operator!=(const flattening_iterator& a,
        const flattening_iterator& b)
    {
        return !(a == b);
    }

private:

    void advance_past_empty_inner_containers()
    {
        while (outer_it_ != outer_end_ && inner_it_ == outer_it_->end())
        {
            ++outer_it_;
            if (outer_it_ != outer_end_)
                inner_it_ = outer_it_->begin();
        }
    }

    outer_iterator outer_it_;
    outer_iterator outer_end_;
    inner_iterator inner_it_;
};

template <typename Iterator>
flattening_iterator<Iterator> flatten(Iterator it)
{
    return flattening_iterator<Iterator>(it, it);
}

template <typename Iterator>
flattening_iterator<Iterator> flatten(Iterator first, Iterator last)
{
    return flattening_iterator<Iterator>(first, last);
}
