import tkinter as tk
from typing import Optional

from threading import Thread
from pygamehack_utils.aob import AOBFinder, AOBScanner
from pygamehack_utils.parser import classes_to_tuples
from pygamehack_utils.type_helpers import is_hackstruct_type

from .core.tree_view import TreeView, TreeViewNode, FIRST_COLUMN
from .variable_view import VariableNode


class AOBDiscoverNode(TreeViewNode):
    def __init__(self, tree: TreeView, name: str, parent=None):
        super().__init__(tree, name, parent)
        self.begin = 0
        self.aob = '??'
        self.node = None

    def set_variable_node(self, node: VariableNode):
        self.node = node

    def update_aob(self, begin: int, aob: str):
        self.begin = begin
        self.aob = aob
        self.set('instruction', f'{begin:0{2 * self.node.variable.address.hack.ptr_size}X}')
        self.set('aob', aob)


class AOBDiscoverView(tk.Frame):

    TITLE = 'AOB Discovery'

    SCAN_THREADS = 4

    def __init__(self, master):
        super().__init__(master)

        self.is_hidden = True
        self.is_debugging = False
        self.is_scanning = False
        self.hack = None
        self.file = None

        title_label = tk.Label(self, text=AOBDiscoverView.TITLE)
        title_label.pack(side=tk.TOP, fill=tk.X, expand=True)

        self.tree = TreeView(self)

        self.tree.node_type = AOBDiscoverNode

        self.tree.add_columns(('instruction', 'Instruction Address'), ('aob', 'AOB'))

        self.tree.column_named(FIRST_COLUMN)\
            .configure(width=200, minwidth=200, stretch=tk.NO)

        self.tree.column_named('instruction')\
            .configure(width=150, minwidth=150, stretch=tk.NO)

        self.tree.column_named('aob')\
            .configure(width=300, minwidth=200, stretch=tk.YES)

        self.buttons = AOBDiscoverViewButtons(self)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.buttons.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def set_hack(self, hack):
        self.hack = hack

    def set_hackstruct_file(self, hackstruct_file):
        self.file = hackstruct_file

    def add_target(self, node: VariableNode, begin: int = 0, aob: str = '??') -> AOBDiscoverNode:
        new_node = self.tree.add_node(node.variable.address.name)  # type: AOBDiscoverNode
        new_node.set_variable_node(node)
        new_node.text = node.property_name
        new_node.update_aob(begin, aob)
        return new_node

    def remove_target(self, node: VariableNode):
        self.tree.remove_node(node.variable.address.name)

    def get_target(self, name: str) -> Optional[AOBDiscoverNode]:
        return self.tree.node_named(name)

    def clear_targets(self):
        self.tree.clear()

    def discover(self):
        if self.is_debugging:
            return
        self.is_debugging = True
        Thread(target=self._find_aob, daemon=True).start()

    def scan(self):
        if self.is_scanning:
            return
        self.is_scanning = True
        Thread(target=self._scan_aob, daemon=True).start()

    def _find_aob(self):
        def find():
            finder = AOBFinder(self.hack)

            for target in self.tree:
                if is_hackstruct_type(target.node.variable):
                    finder.add_target(target.node.variable)
                else:
                    finder.add_target(target.node.variable.address)

            return finder.find_all()

        results = self.file.generate_aob(find)

        for result in results:
            offset_path = self.file.address_path_to_aob_path(result['name'])
            aob_class_name, property_name = offset_path.split('.')[-2:]
            data = self.file.aob[aob_class_name].fields[property_name].data
            self.get_target(result['name']).update_aob(data['begin'], data['aob'])

        self.is_debugging = False

    def _scan_aob(self):
        def scan(aob_classes):
            scanner = AOBScanner(self.hack.process_name)

            for name, data in classes_to_tuples(aob_classes):
                scanner.add_aob(name=name, aob_string=data['aob'], **data)

            return scanner.scan(n_threads=AOBDiscoverView.SCAN_THREADS)

        results = self.file.update_offsets(scan, reload_when_complete=False)

        # TODO: Update hackstructs after scan

        self.is_scanning = False


class AOBDiscoverViewButtons(tk.Frame):
    def __init__(self, master):
        super().__init__(master, width=250)
        self.view = master

        clear_button = tk.Button(self, text='Clear', command=self.view.clear_targets)
        clear_button.pack(side=tk.BOTTOM, fill=tk.X, expand=False, padx=10, pady=20)

        search_button = tk.Button(self, text='Discover', command=self.view.discover)
        search_button.pack(side=tk.TOP, fill=tk.X, expand=False, padx=10, pady=20)
