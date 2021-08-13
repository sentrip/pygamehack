
# pygamehack
**pygamehack** is a simple, dependency free Python 3.7+ library for reading/writing memory and binary analysis of running processes. 

```python
import pygamehack as gh

hack = gh.Hack()
hack.attach("MyProgram.exe")
print(hack.read_u32(0xdeadbeef))
``` 

pygamehack provides a simple API to read/write the memory of a process externally to the process. This can be done manually, or using named variables and a type hierarchy that that you define. You can entirely replicate the structure of an arbitrary compiled program in Python using a familiar dataclass-based type annotation syntax. 

The goal of pygamehack is to prevent you from ever having to repeat tedious/manual labor tasks that are common when reverse engineering binary programs.

pygamehack also provides various tools for binary analysis, and defines a workflow for fully automating the tedious work of updating hard-coded values in a reverse-engineering project. 

pygamehack also understands the file formats of some common reverse engineering tools (CheatEngine, ReClassNet) and allows you to quickly get started hacking in Python without having to redo any tedious manual labor.

## Installation
pygamehack can be installed with pip.
```shell
pip install pygamehack
```

## Features
* Read/write process memory externally to the process.
* Replicate a program's structure externally to the program
* Named variables in Python that modify the memory of a target process
* Familiar, dataclass based syntax in Python to define the structure of any compiled program


## Core
pygamehack defines a few primary types that can then be used to build up the structure of any program. These types are **Hack**, **Address**, **Buffer**. There is also the concept of a ***Variable***, which is an abstract representation of a typed memory region. pygamehack provides variable implementations for all of the basic numeric types, as well as strings, buffers and arrays. For more details see the Variable section.

### Basic Types
A basic type is a numeric type. All naming conventions for types are based on the names of the basic types. pygamehack defines the following basic types:

| Name | C-type | Size (bytes)
---------|--------:|------:
i8 | int8_t | 1
i16 | int16_t | 2
i32 | int32_t | 4
i64 | int64_t | 8
u8 | uint8_t | 1
u16 | uint16_t | 2
u32 | uint32_t | 4
u64 | uint64_t | 8
bool | bool | 1
float | float | 4
double | double | 8
usize | size_t | 4 or 8
ptr | void* | 4 or 8

There are 2 more types - **str** and **buf** - that have names that are used in the previously mentioned naming conventions, but are not numeric types. **str** represents a string (i.e. an array of characters) and **buf** represents an array of u8.

### Hack
This is the primary interface to an external process' memory.  Before reading/writing memory you must first attach to the target process 

```python
import pygamehack as gh

hack = gh.Hack()
hack.attach("MyProgram.exe")
# or you can use the Process ID
hack.attach(12345)
``` 

#### Reading/writing memory
For every basic type, there are corresponding 'Hack.read_NAME' and 'Hack.write_NAME' methods that can be used to read/write memory.
```python
import pygamehack as gh
hack = gh.Hack()
# Read 
value = hack.read_u32(0xdeadbeef)
# Write
hack.write_u32(0xdeadbeef, 999)
``` 

#### Scanning memory

### Address
This type is the representation of a memory address (I.e. A pointer) in the target process' memory. Addresses that depend on program parameters or runtime values must be **loaded**. There are 3 types of addresses:
+ Manual
+ Static
+ Dynamic

#### Manual
A manual address is what it sounds like, a hard-coded numeric value that represents a memory address in the target process. To create a manual address you need to provide the value of the address.

```python
import pygamehack as gh
hack = gh.Hack()

address = gh.Address(hack, 0xdeadbeef)
``` 

> <span style="color:orange"> NOTE: Because of practices like ASLR (address space layout randomization), it is recommended that you only use manual addresses when debugging or prototyping, as the address will likely stop working the next time that you run the target program. </span>

#### Static

A static address represents an offset into the memory region of a process, or any of the dynamic libraries loaded into the target process' memory space. To create a static address, you need a module name and an offset.

```python
import pygamehack as gh
hack = gh.Hack()

address = gh.Address(hack, "MyProgram.exe", 0xbeef)
``` 

Static addresses are the starting point of any program, and can be used to access data that has been compiled directly into the program binary. You can use static addresses as a base for all of the other interesting addresses.


#### Dynamic

A dynamic address represents an arbitrary memory address that depends on the value of another address in the target process' memory. The address is calculated by following an offset path in memory starting with the value of the parent address. To create a dynamic address, you need a parent address and a list of offsets.

```python
import pygamehack as gh
hack = gh.Hack()

address = gh.Address(hack, "MyProgram.exe", 0xbeef)
d_address = gh.Address(address, [0x4])
``` 

#### Address loading

Each address type is created with different arguments and will respond differently to being loaded:

| Type        | Requires    | Operation
|------------|-------------|------------
| Manual | Nothing |None
| Static | Base Address | Query base address using library name
| Dynamic | Valid Parent Address| (Load parent address), follow offset path

To load an address:
```python
import pygamehack as gh
hack = gh.Hack()

address = gh.Address(hack, "MyProgram.exe", 0xbeef)
# Load
address.load()
# Get loaded value
print(address.value)
# Check if valid
print(address.valid)
``` 

#### Automatically loading addresses
When you have a lot of address objects and want to update them all in bulk, or you simply want to avoid calling 'Address.load()' every time you want to use an address, you can enable **address auto loading**.

When you call 'Hack.update()', every address that has been marked for auto loading will reload its value. You can conditionally load subsets of addresses by setting the 'Address.<>TODO<>' property.

### Buffer
A buffer is a handle to dynamically allocated memory. Since memory cannot be accessed directly in Python, buffers provide a convenient interface for reading typed values from arbitrary memory. There are two types of buffers, an **owning buffer** and a **view buffer**. 

#### Owning buffer
An **owning buffer** must explicitly read from the target process memory to update its contents. It will never observe changes in the contents of another buffer's memory. 

To create an **owning buffer**, you only need to provide the size of the buffer.

```python
import pygamehack as gh
hack = gh.Hack()

buffer = gh.Buffer(hack, 32)
``` 

#### View buffer
A **view buffer** is a view into the memory of another buffer, and will observe changes to its memory when its parent reads from the target process. View buffers also allow for a number of useful internal optimizations. 

To create a **view buffer**, you must provide a parent buffer, an offset into the parent buffer, and the size of the buffer.

```python
import pygamehack as gh
hack = gh.Hack()

buffer = gh.Buffer(hack, 32)
v_buffer = gh.Buffer(buffer, 8, 16)
``` 
#### Reading/writing buffers
Buffers are like memory middle-men in pygamehack. Like a Hack, a Buffer has 'read_' and 'write_' methods for all of the basic types. Unlike a Hack, calling 'read_' and 'write_' on a Buffer will not read/write the target process memory. These methods operate on the buffer's local storage, and if you want to read/write the target process memory you must do so explicitly using the 'Buffer.read_from()' and 'Buffer.write_to()' methods. 

```python
import pygamehack as gh
hack = gh.Hack()

# ... attach ...

addr = 0xdeadbeef
buffer = gh.Buffer(hack, 32)

# 0 since buffer has not read from process
assert buffer.read_u32(0) == 0
# Read entire content of buffer from process
buffer.read_from(addr)
# Buffer has data ready to read
value = buffer.read_u32(0)

# Write a new value to local storage
buffer.write_u32(0, 5)
# Process unaffected
assert hack.read_u32(addr) == value
# Write entire content of buffer to process
buffer.write_to(addr)
# Process has been updated
assert hack.read_u32(addr) == 5
``` 

### Variables