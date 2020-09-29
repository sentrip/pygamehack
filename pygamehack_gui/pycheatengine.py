import psutil
from simpleeval import simple_eval

import os
import logging
import tkinter as tk
from tkinter import filedialog
from tkinter.simpledialog import Dialog

import pygamehack as gh
from pygamehack_utils import HackStruct
from pygamehack_utils.debug_view import DebuggableVariable
from pygamehack_utils.hackstruct_file import HackStructFile
from pygamehack_utils.type_helpers import is_hackstruct_type

from .core.tree_view import TreeView, FIRST_COLUMN

from .aob_discover_view import AOBDiscoverView
from .log_view import LogWindow
from .variable_view import VariableTreeView


UPDATE_INTERVAL = 20
DELETE = '.'

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)
logging.getLogger('pygamehack').propagate = True


def parse_address_string(hack: gh.Hack, address_string: str) -> int:
    part = ''
    will_dereference = False
    for char in address_string:
        if char == '[':
            will_dereference = True
        elif char == ']':
            if not will_dereference:
                raise RuntimeError(f"Missing '[' in {address_string}")
            address = hack.read_ptr(simple_eval(part))
            will_dereference = False
            part = str(address)
        else:
            part += char
    return simple_eval(part)


def gui_main(process_name=None, hackstruct_file_name=None):
    engine = PyCheatEngine()

    if process_name is not None:
        engine.attach(process_name)

    if hackstruct_file_name is not None:
        engine.load_file(hackstruct_file_name)

    engine.run()


class PyCheatEngine(tk.Tk):
    def __init__(self):
        super().__init__()
        self._running = False
        self._hack = None
        self._file = None
        self._key_handlers = {}

        self.wm_title('PyCheatEngine')

        self.menu = PyCheatEngine.TopLevelMenu(self)

        self.aob_view = AOBDiscoverView(self)

        self.variable_view = VariableTreeView(self)

        self.variable_view.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.bind('<Button-1>', lambda e: self._clear_opposite_scans())
        self.bind('<Key>', lambda e: self._key_handlers.get(e.keycode, lambda: None)())

        self.bind_key('A', lambda: self._toggle_scans(self.variable_view.selected()))
        self.bind_key('H', lambda: self._toggle_hex_display(self.variable_view.selected()))
        self.bind_key('L', lambda: self._toggle_show_value(self.variable_view.selected()))
        self.bind_key(DELETE, lambda: self._toggle_scans([n.node for n in self.aob_view.tree.selected()]))
        self.bind_key('Z', self._toggle_aob_discover)
        self.bind_key('U', self._toggle_animations)

    def attach(self, process_name):
        if self._hack is None:
            self._hack = gh.Hack(process_name)
            self.aob_view.set_hack(self._hack)
        else:
            self._hack.process_name = process_name
        self._hack.attach()

    def load_file(self, hackstruct_file):
        self._file = HackStructFile(hackstruct_file)
        self._file.load()
        self.aob_view.set_hackstruct_file(self._file)

        self._hack.clear_addresses()
        self.variable_view.clear()
        self.aob_view.clear_targets()

        self._file.add_addresses(self._hack)
        self._hack.load_addresses()
        self._add_variables_from_file()

    def run(self):
        self._start_updating()
        self.mainloop()

    def bind_key(self, key: str, handler):
        self._key_handlers[ord(key.upper())] = handler

    def _add_variables_from_file(self):
        root_variables = [r(self._hack) for r in self._file.root_structs]

        for variable in root_variables:
            for name, v in HackStruct.iter_variables(variable):
                address = getattr(v, 'address', None)
                if (
                        address is None
                        or self.variable_view.node_named(address.name)
                        or (is_hackstruct_type(v.__class__) and not isinstance(v, DebuggableVariable))
                ):
                    continue

                self.variable_view.add_variable(v)

    def _clear_opposite_scans(self):
        if self.aob_view.focus_get() != self.aob_view.tree and self.aob_view.tree.selection():
            self.aob_view.tree.selection_remove(self.aob_view.tree.selection())

        if self.variable_view.focus_get() != self.variable_view and self.variable_view.selection():
            self.variable_view.selection_remove(self.variable_view.selection())

    def _toggle_animations(self):
        selected = self.variable_view.selected()
        if selected:
            for node in selected:
                node.show_updates = not node.show_updates
        else:
            self.variable_view.show_updates = not self.variable_view.show_updates

    def _toggle_aob_discover(self):
        if self.aob_view.is_hidden:
            self.aob_view.is_hidden = False
            self.aob_view.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        else:
            self.aob_view.is_hidden = True
            self.aob_view.pack_forget()

    def _toggle_hex_display(self, variables):
        for node in variables:
            node.show_value_as_hex = not node.show_value_as_hex

    def _toggle_show_value(self, variables):
        for node in variables:
            node.show_value = not node.show_value

    def _toggle_scans(self, variables):
        has_scans = False

        for node in variables:
            target = self.aob_view.get_target(node.variable.address.name)
            if target is None and node.parent:
                self.aob_view.add_target(node, *self._aob_data_for_node(node))
                has_scans = True
            elif target is not None:
                self.aob_view.remove_target(node)

        if has_scans and self.aob_view.is_hidden:
            self._toggle_aob_discover()

    def _start_updating(self):
        self._running = True
        self._loop()

    def _loop(self):
        if not self._running:
            return

        if self._hack.is_attached:
            self._hack.load_addresses()
            self.variable_view.update_nodes()
            self.after(UPDATE_INTERVAL, self._loop)

    def _loaded_struct_for_node(self, node):
        return self._file.structs.get(node.parent.variable.__class__.__name__, None)

    def _aob_data_for_node(self, node):
        struct = self._loaded_struct_for_node(node)
        if struct is not None:
            aob_data = struct.aob.fields[node.property_name].data
            return aob_data['begin'], aob_data['aob']
        else:
            return 0, '??'

    class TopLevelMenu(tk.Menu):
        def __init__(self, master):
            super().__init__(master)
            self.master.config(menu=self)
            self.log_window = None

            file_menu = tk.Menu(self, tearoff=False)
            file_menu.add_command(label="Attach...", command=self.attach_to_process)
            file_menu.add_command(label="Open...", command=self.load_hackstruct_file)
            self.add_cascade(label="File", menu=file_menu)

            options_menu = tk.Menu(self, tearoff=False)
            options_menu.add_command(label="Log", command=self.create_log_window)
            options_menu.add_command(label="Update offsets (AOB scan)", command=lambda: self.master.aob_view.scan())
            self.add_cascade(label="Options", menu=options_menu)

        def attach_to_process(self):
            process_name = ProcessDialog(self.master).process_name

            if process_name:
                self.master.attach(process_name)

        def create_log_window(self):
            if self.log_window is None:
                self.log_window = LogWindow(self.master)
            elif self.log_window.state == tk.NORMAL:
                self.log_window.focus_set()

        def load_hackstruct_file(self):
            file_name = filedialog.askopenfilename(
                initialdir=os.getcwd(),
                title='Select hackstruct file',
                filetypes=[('Python files', '*.py')]
            )

            if file_name and file_name.endswith('.py'):
                self.master.load_file(file_name)


class ProcessDialog(Dialog):

    def __init__(self, master):
        self.process_name = ''
        self.process_list = None
        super().__init__(master, title='Attach to process...')

    def body(self, master):
        self.process_list = ProcessList(self)

        self.process_list.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.process_list.list.bind('<Double-Button-1>', self.ok)

        return self.process_list.list

    def apply(self):
        self.process_name = self.process_list.get_process_name()

    def buttonbox(self):
        ok_button = tk.Button(self, text='OK', command=self.ok)
        exit_button = tk.Button(self, text='Exit', command=self.cancel)

        exit_button.pack(side=tk.BOTTOM, fill=tk.X, expand=True)
        ok_button.pack(side=tk.BOTTOM, fill=tk.X, expand=True)


class ProcessList(tk.Frame):
    def __init__(self, master):
        super().__init__(master)

        scrollbar = tk.Scrollbar(self)

        self.list = TreeView(self, yscrollcommand=scrollbar.set, selectmode='browse')

        scrollbar.config(command=self.list.yview)

        self.list.add_columns(('pid', 'ID'), ('name', 'Name'))

        self.list.column_named(FIRST_COLUMN) \
            .configure(width=40, minwidth=0, stretch=tk.NO) \
            .configure_header(text='')

        self.list.column_named('pid') \
            .configure(width=60, minwidth=60, stretch=tk.NO)

        self.list.column_named('name') \
            .configure(width=200, minwidth=200, stretch=tk.YES)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.list.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.populate()

    def populate(self):
        processes = []
        for process in psutil.process_iter():
            processes.append(process)

        processes.sort(key=lambda p: p.create_time())

        for process in processes:
            node = self.list.add_node(str(process.pid))
            node.process = process
            node.set('pid', process.pid)
            node.set('name', process.name())

        self.list.see(str(processes[-1].pid))

    def get_process_name(self):
        return self.list.node_named(self.list.selection()[0]).get('name')
