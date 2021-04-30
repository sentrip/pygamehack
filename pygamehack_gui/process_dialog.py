import tkinter as tk
from tkinter.simpledialog import Dialog
import pygamehack as gh

from .core.tree_view import TreeView, FIRST_COLUMN


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
        for process in gh.Process.all():
            processes.append(process)

        processes.sort(key=lambda p: gh.Process.created_at(p.id))

        for process in processes:
            node = self.list.add_node(str(process.id))
            node.process = process
            node.set('pid', process.id)
            node.set('name', process.name)

        self.list.see(str(processes[-1].id))

    def get_process_name(self):
        return self.list.node_named(self.list.selection()[0]).get('name')
