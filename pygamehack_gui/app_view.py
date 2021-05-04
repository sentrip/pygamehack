import tkinter as tk
import pygamehack as gh
from .address_view import AddressView
from .variable_view import VariableTreeView
from .class_view import ClassView
from .process_dialog import ProcessDialog


class IntTypes(gh.Struct):
    num_i8 : gh.i8  =  0
    num_i16: gh.i16 =  2
    num_i32: gh.i32 =  4
    num_i64: gh.i64 =  8
    num_u8 : gh.u8  = 16
    num_u16: gh.u16 = 18
    num_u32: gh.u32 = 20
    num_u64: gh.u64 = 24

class TestProgram(gh.Struct):
    marker: gh.uint         = 0x0
    flag  : gh.uint         = 0x8
    update: gh.uint         = 0xC
    n     : IntTypes        = 0x10



class App(tk.Tk):
    WIDTH = 1200
    HEIGHT = 900

    def __init__(self):
        super().__init__()
        
        self.debug()

        self.setup_window()

        self.menu = TopLevelMenu(self)
        self.view_addresses = AddressView(self)
        self.view_variables = VariableTreeView(self)
        # self.view_classes = ClassView(self)
        
        self.view_addresses.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.view_variables.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        # self.view_classes.frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def setup_window(self):
        self.wm_title('pygamehack_gui')

        w, h = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f'{App.WIDTH}x{App.HEIGHT}+{w // 2 - App.WIDTH // 2 - 650}+{h // 2 - App.HEIGHT // 2}')

    def debug(self):
        import pygamehack as gh
        with open('MarkerAddress-64.txt') as f:
            marker_addr = int(f.read())

        self.hack = gh.Hack()
        self.root_address = gh.Address(self.hack, marker_addr)

        self.struct = TestProgram(self.root_address)
        self.struct.address.name = "TestProgram"

    def run(self):
        self.mainloop()


class TopLevelMenu(tk.Menu):
    def __init__(self, master):
        super().__init__(master, tearoff=False)
        self.master.config(menu=self)

        file_menu = tk.Menu(self, tearoff=False)
        file_menu.add_command(label="Attach...", command=self.attach_to_process)
        self.add_cascade(label='File', menu=file_menu)

    def attach_to_process(self):
        process_name = ProcessDialog(self.master).process_name

        if process_name:
            if self.master.hack.process.attached:
                self.master.hack.detach()
            self.master.hack.attach(process_name)
            self.master.view_variables.update()
