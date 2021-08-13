#ifndef PYVARIABLEARRAY_H
#define PYVARIABLEARRAY_H

#include <pybind11/pybind11.h>

#include "../Address.h"
#include "../Process.h"
#include "../Variable.h"

namespace py = pybind11;

namespace pygamehack {

class PyVariableArray : public VariableBufferBase {
public:
    struct iterator;

    PyVariableArray(Address& address, usize size, py::kwargs& kwargs):
        VariableBufferBase{address, 1}
    {
        init(size, kwargs);
    }

    PyVariableArray(PyVariableArray& parent, uptr offset, usize size, py::kwargs& kwargs):
        VariableBufferBase{parent, offset, 1}
    {
        init(size, kwargs);
    }

    bool detect_buffer_subclass(usize size, py::kwargs& kwargs)
    {
        static constexpr auto check_attr = [](py::object& obj, const char* name)
        {
            return py::hasattr(obj, name) && py::cast<bool>(obj.attr(name));
        };

        if (check_attr(value_type, "is_basic")) {
            return false;
        }

        auto set_non_basic_value_type = [&](){
            is_value_type_basic = false;
            values = py::list(size);
            value_type_size = py::cast<usize>(value_type.attr("size"));
            for (usize i = 0; i < size; ++i) { values[i] = py::none(); }
            value.unsafe_force_resize(size * value_type_size);
        };

        if (check_attr(value_type, "is_container") || check_attr(value_type, "is_buffer_class")) {
            is_value_type_buffer_or_container = true;
            set_non_basic_value_type();
            return true;
        }

        py::dict modules = py::module_::import("sys").attr("modules");
        py::module m = modules["pygamehack.c"];
        py::function issubclass = modules["builtins"].attr("issubclass");
        py::object type_type = modules["builtins"].attr("type");
        const char* names[5]{"buf", "str", "c_str", "arr", "c_arr"};
        for (const auto* name: names) {
            py::object c = m.attr(name);
            if (check_attr(value_type, "is_container") || (py::isinstance(value_type, type_type) && py::cast<bool>(issubclass(value_type, c)))) {
                is_value_type_buffer_or_container = true;
                set_non_basic_value_type();
                return true;
            }
        }

        return false;
    }

    bool detect_basic_type(usize size, py::kwargs& kwargs)
    {
        string type_name = py::cast<string>(value_type.attr("__name__"));

        #define F(type, name) \
        if (type_name == name) { \
            read_func = &PyVariableArray::read_basic<type>; \
            write_func = &PyVariableArray::write_basic<type>; \
            is_value_type_basic = true; \
            if constexpr (std::is_same_v<type, Ptr>) { value_type_size = address().process().get_ptr_size(); } \
            else if constexpr (std::is_same_v<type, string>) { value_type_size = value_type.attr("size").cast<usize>(); } \
            else { value_type_size = sizeof(type); } \
            value.unsafe_force_resize(size * value_type_size); \
            return true; \
        }

        FOR_EACH_INT_TYPE(F)
        F(Ptr, "ptr")
        F(string, "str")
        #undef F
        return false;
    }

    void init(usize size, py::kwargs& kwargs)
    {
        value_type = kwargs["type"];

        if (detect_buffer_subclass(size, kwargs)) return;
        if (detect_basic_type(size, kwargs)) return;

        value_type_size = py::cast<usize>(value_type.attr("size"));
        values = py::list(size);
        for (usize i = 0; i < size; ++i) { values[i] = py::none(); }
        value.unsafe_force_resize(size * value_type_size);
    }

    static PyVariableArray create(py::object& address, usize size, py::kwargs& kwargs)
    {
        if (address.is_none()) {
            // TODO: Verify VariableArray kwargs
            return PyVariableArray{kwargs["parent_buffer"].cast<PyVariableArray&>(), kwargs["offset_in_parent"].cast<usize>(), size, kwargs};
        }
        else {
            return PyVariableArray{address.cast<Address&>(), size, kwargs};
        }
    }

    Buffer& buffer()
    {
        return value;
    }

    PyVariableArray& get()
    {
        return *this;
    }

    PyVariableArray& read(usize n, usize starting_at)
    {
        VariableBufferBase::read(n * value_type_size, starting_at * value_type_size);
        return *this;
    }

    void write(py::list& vs, usize starting_at)
    {
        PGH_ASSERT(starting_at + vs.size() <= length(), "Writing too many values to array");
        if (is_value_type_basic) {
            for (usize i = 0; i < vs.size(); ++i) {
                py::object ob(vs[i]);
                write_func(*this, (starting_at + i) * value_type_size, ob);
            }
        }
        else {
            for (usize i = std::max<usize>(starting_at, values.size() - 1); i < starting_at + vs.size(); ++i) {
                values.append(std::move(create_element(i)));
            }
            for (usize i = 0; i < vs.size(); ++i) {
                py::object ob(vs[i]);
                values[starting_at + i].attr("write")(ob);
            }
        }
    }

    void flush(usize n, usize starting_at)
    {
        VariableBufferBase::flush(n * value_type_size, starting_at * value_type_size);
    }

    void reset()
    {
        value.clear();
        if (is_value_type_basic) {
            for (usize i = 0; i < values.size(); ++i) { values[i] = py::none(); }
        }
    }

    usize length() const
    {
        return value.size() / value_type_size;
    }

    py::object getitem(usize n)
    {
        if (is_value_type_basic) {
            if (n >= length()) throw py::index_error{};
            return read_func(*this, n * value_type_size);
        }
        else {
            ensure_element(n);
            if (is_value_type_buffer_or_container) {
                return values[n].attr("get")();
            }
            else {
                return values[n].attr("read")();
            }
        }
    }

    py::object getitem(py::slice slice) const
    {
        if (is_value_type_basic) {
            py::ssize_t start, stop, step, slicelength;
            if (!slice.compute(length(), &start, &stop, &step, &slicelength))
                throw py::error_already_set();
            py::list sliced(slicelength);
            iterator begin{this, start, static_cast<i64>(step)}, end{this, stop};
            for (auto it = begin; it != end; ++it) sliced.append(*it);
            return sliced;
        }
        else {
            return values[slice];
        }
    }

    void setitem(usize n, py::object& item)
    {
        if (is_value_type_basic) {
            if (n >= length()) throw py::index_error{};
            write_func(*this, n * value_type_size, item);
        }
        else {
            ensure_element(n);
            values[n].attr("write")(item);
        }
    }

    struct iterator {
        const PyVariableArray* array{};
        i64 index{};
        i64 step{1};

        // Deref
        py::object operator*() const { return array->read_func(*array, index * array->value_type_size); }
        // Pre increment
        iterator& operator++() { index += step; return *this; }
        // Equality
        bool operator==(const iterator& other) const { return array == other.array && index == other.index; }
        bool operator!=(const iterator& other) const { return !(*this == other); }
    };

    py::object iter()
    {
        if (is_value_type_basic) {
            return py::make_iterator(iterator{this, 0}, iterator{this, i64(length())});
        }
        else {
            return values.attr("__iter__");
        }
    }

    string tostring()
    {
        string s{"["};
        auto it = iter();
        usize i = 0;
        for (auto& v: it) {
            if ((i++) != 0) s.append(", ");
            s.append(py::cast<string>(v.attr("__str__")()));
        }
        s.append("]");
        return s;
    }

    bool operator==(const py::object& other)
    {
        if (!py::isinstance<PyVariableArray>(other) && !py::isinstance<py::list>(other)) {
            return false;
        }
        if (py::len(other) != length()) {
            return false;
        }
        if (!is_value_type_basic) {
            return values == other;
        }
        usize i = 0;
        for (const auto& obj: py::iter(other)) {
            if (obj != getitem(i++)) {
                return false;
            }
        }
        return true;
    }

    bool operator!=(const py::object& other)
    {
        return !(*this == other);
    }

private:
    py::object create_element(usize i)
    {
        py::kwargs kwargs{};
        kwargs["buffer"] = true;
        kwargs["parent_buffer"] = (PyVariableArray&)*this;
        kwargs["offset_in_parent"] = i * value_type_size;
        return value_type(py::none(), **kwargs);
    }

    void ensure_element(usize n)
    {
        while (n >= values.size()) {
            values.append(py::none());
        }

        values[n] = std::move(create_element(n));
    }

    template<typename T>
    static py::object read_basic(const PyVariableArray& arr, usize i)
    {
        if constexpr(std::is_same_v<T, Ptr>) { return py::cast(arr.value.read_ptr(i)); }
        else if constexpr(std::is_same_v<T, string>) { return py::cast(arr.value.read_string(i)); }
        else {
            T v{};
            arr.value.read<T>(i, v);
            return py::cast(v);
        }
    }

    template<typename T>
    static void write_basic(PyVariableArray& arr, usize i, py::object& obj)
    {
        if constexpr(std::is_same_v<T, Ptr>) { arr.value.write_ptr(i, obj.cast<uptr>()); return; }
        else if constexpr(std::is_same_v<T, string>) { arr.value.write_string(i, obj.cast<string>()); return; }
        else if constexpr(std::is_same_v<T, Buffer>) { arr.value.write_buffer(i, obj.cast<Buffer&>()); return; }
        else {
            T v = obj.cast<T>();
            arr.value.write_value<T>(i, v);
        }
    }

private:
    friend struct iterator;
    using VariableBufferBase::value;
    using VariableBufferBase::_address;
    using VariableBufferBase::_parent;

    py::object(*read_func)(const PyVariableArray&, usize) = nullptr;
    void(*write_func)(PyVariableArray&, usize, py::object&) = nullptr;
    usize value_type_size{};
    py::object value_type;
    py::list values;
    bool is_value_type_basic{};
    bool is_value_type_buffer_or_container{};
};

}

#endif
