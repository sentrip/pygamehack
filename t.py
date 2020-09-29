import pygamehack as gh
from pygamehack_utils import HackStruct, Ptr, TypeHintContainer, ArrayVariable

from pygamehack_extensions.raw_string import const_c_str, c_str
from pygamehack_extensions.raw_array import Array


"""
class CPPVector(ArrayVariable):
    size = 8 * 4

    def __init__(self, t, address):
        self.begin = 0
        self.end = 0
        self.dynamic_type = t
        self.address = address
        self.memory_address = self.address.hack.get_or_add_dynamic_address(f'{self.address.name}/m', self.address, [0x0])
        self.address.dynamic_offset = self.address.hack.ptr_size

    def read_values(self):
        # Update pointers
        previous_begin, previous_end, previous_size = self.begin, self.end, self.vector_size
        self.begin, self.end = self.get_begin_end()
        # Create
        if not self.variables:
            self.add_n(self.vector_size)
        # Grow
        elif self.vector_size > previous_size:
            self.add_n(self.size - previous_size, starting_at=previous_size)
        # Read elements
        for v in self.variables[:self.vector_size]:
            v.read()

    def __getitem__(self, key):
        return self.variables[key].get()

    def __setitem__(self, key, value):
        self.variables[key].write(value)
    
    def __iter__(self):
        for v in self.variables:
            yield v.get()

    def add_n(self, n, starting_at = 0):
        for i in range(starting_at, starting_at + n):
            address = self.address.hack.get_or_add_dynamic_address(f'{self.memory_address.name}/{i}', self.memory_address, [])
            address.dynamic_offset = i * self.dynamic_type.size
            self.variables.append(self.dynamic_type(address))

    def get_begin_end(self):
        return self.address.hack.read_ptr(self.address.address), self.address.hack.read_ptr(self.address.address + self.address.hack.ptr_size)

    @property
    def vector_size(self):
        return int((self.end - self.begin) / self.type.size)


class Vector(metaclass=TypeHintContainer):
    types = { CPPVector.size: CPPVector }
"""



class Powers(metaclass=HackStruct):
    power_0: gh.uint = 0x0
    power_1: gh.uint = 0x4
    power_2: gh.uint = 0x8
    power_3: gh.uint = 0xC
    power_4: gh.uint = 0x10




class Game(metaclass=HackStruct):
    selected_index: gh.uint = 0x0


class App(metaclass=HackStruct):
    address = 'app'

    powers: Powers = 0x0
    str_1: c_str = 0x48
    const_str_1: const_c_str = 0x50
    values: Ptr[Array[gh.uint32, 8]] = 0x58


HackStruct.define_types()


hack = gh.Hack("TestProgram-64.exe")

marker_addr = hack.add_static_address("marker", hack.process_name, 0xA000)
hack.add_static_address("app", hack.process_name, 0xA100)


# Variables

marker_v = gh.uint(marker_addr)

hack.attach()

print(marker_v.read())


# HackStruct

app = App(hack)
app.address.previous_holds_ptr = False

hack.load_addresses()

app.values.auto_update = True
app.values.read_contents()
help(App.powers.power_0)
help(App.values)
print(app.values[3], len(app.values))



#app.buffer.read()

#hack.load_addresses()
#app.game.buffer.read()

#print(app.game.selected_index)


#hack.load_addresses()
#app.powers.buffer.read()

#print(app.powers.power_0)

#print(app.str_1, len(app.str_1))
#print(app.const_str_1, len(app.const_str_1))

previous = app.str_1

app.str_1 = 'something else'

#print(app.str_1)

app.str_1 = previous


# Vector

#app.values.read_values()

#hack.load_addresses()

#app.values.read_values()

#print(app.values[10])


# Buffer

powers_addr = hack.add_dynamic_address('powerss', app.address, [])

buf_v = gh.buffer(powers_addr, 5 * gh.uint.size)

hack.load_addresses()

#print(buf_v.read().read_uint32(0x0))


# Buffer auto-defined

#powers = Powers(powers_addr)

#hack.load_addresses()

#powers.buffer.read()

#print(powers.power_1)







