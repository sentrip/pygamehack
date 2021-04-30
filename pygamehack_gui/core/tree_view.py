import tkinter as tk
import tkinter.ttk as ttk

from typing import Any, Callable, Optional


FIRST_COLUMN = 'First'
NODE_DEFAULT_TAG = '__tree_view_node'


class TreeViewColumn(object):

    name: str
    header: str

    def __init__(self, tree: 'TreeView', name: str, header: str):
        self.tree = tree
        self._name = '0' if name == FIRST_COLUMN else name
        self._header = header
        self.configure_header(text=self._header, anchor=tk.W)

    def configure(self, **kwargs) -> 'TreeViewColumn':
        self.tree.column(self._name, **kwargs)
        return self

    def configure_header(self, **kwargs) -> 'TreeViewColumn':
        self.tree.heading(self.name, **kwargs)
        return self

    @property
    def header(self) -> str:
        return self._header

    @header.setter
    def header(self, value: str):
        self._header = value
        self.configure_header(text=self._header)

    @property
    def name(self) -> str:
        return ('#' if self._name == '0' else '') + self._name


class TreeViewNode(object):

    name: str
    text: str
    parent: Optional['TreeViewNode']

    def __init__(self, tree: 'TreeView', name: str, parent: Optional['TreeViewNode'] = None):
        self.tree = tree
        self._name = name
        self._text = ''
        self._parent = parent

    def on_column_update(self, column: TreeViewColumn, node: 'TreeViewNode'):
        pass

    @property
    def name(self) -> str:
        return self._name

    @property
    def parent(self) -> Optional['TreeViewNode']:
        return self._parent

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str):
        self._text = value
        self.tree.item(self._name, text=value)

    def after(self, milliseconds: int, callback: Callable, *args: Any):
        self.tree.after(milliseconds, callback, *args)

    def configure(self, **kwargs) -> 'TreeViewNode':
        self.tree.tag_configure(self._name, **kwargs)
        return self

    def get(self, column: str) -> Any:
        return self.tree.set(self.name, column)

    def set(self, column: str, value: Any):
        current_value = self.get(column)

        if value != current_value:

            self.tree.set(self.name, column, value)

            if current_value:
                self.on_column_update(self.tree.column_named(column), self)


class TreeView(ttk.Treeview):

    def __init__(self, master, **kwargs):
        _fix_tree_view_colors()
        super().__init__(master, **kwargs)

        self.node_type = TreeViewNode

        self._nodes = {}
        self._columns = {FIRST_COLUMN: TreeViewColumn(self, FIRST_COLUMN, 'Name')}

        self.can_right_click = False
        self.show_right_click_popup = True
        self.right_clicked_node = None
        self.right_click_menu = tk.Menu(self, tearoff=False)

        self.tag_bind(NODE_DEFAULT_TAG, '<Double-Button-1>', self._on_double_click)
        self.tag_bind(NODE_DEFAULT_TAG, '<Button-3>', self._on_right_click)
        self.tag_bind(NODE_DEFAULT_TAG, '<<TreeviewOpen>>', self._on_open_node)
        self.tag_bind(NODE_DEFAULT_TAG, '<<TreeviewClose>>', self._on_close_node)
        self.tag_bind(NODE_DEFAULT_TAG, '<<TreeviewSelect>>', lambda e: self.on_select())

    def __contains__(self, item):
        return item in self._nodes

    def __iter__(self):
        return self._nodes.values().__iter__()

    def __len__(self):
        return len(self._nodes)

    # Input

    def on_select(self):
        pass

    def on_open_node(self, node: 'TreeViewNode'):
        pass

    def on_close_node(self, node: 'TreeViewNode'):
        pass

    def on_double_click(self, column: TreeViewColumn, node: 'TreeViewNode'):
        pass

    def on_right_click(self, column: TreeViewColumn, node: 'TreeViewNode'):
        pass

    def _on_open_node(self, event=None):
        self.on_open_node(self.node_named(self.focus()))

    def _on_close_node(self, event=None):
        self.on_close_node(self.node_named(self.focus()))

    def _on_double_click(self, event=None):
        self.on_double_click(self.column_at(event.x), self.node_at(event.x, event.y))

    def _on_right_click(self, event=None):
        if not self.can_right_click:
            return

        self.right_clicked_node = self.node_at(event.x, event.y)
        self.on_right_click(self.column_at(event.x), self.right_clicked_node)

        if not self.show_right_click_popup:
            return

        try:
            self.right_click_menu.update()
            x_offset = 60#int(self.right_click_menu.winfo_reqwidth() / 2.0)
            # TODO: Right click menu inverted offset when close to bottom of screen
            y_offset = 10
            self.right_click_menu.tk_popup(event.x_root + x_offset, event.y_root + y_offset, 0)
        finally:
            self.right_click_menu.grab_release()

    # Column

    def add_columns(self, *columns: [(str, str)]):
        self['columns'] = tuple(c[0] for c in columns)
        for name, header in columns:
            column = TreeViewColumn(self, name, header)
            self._columns[name] = column

    def column_at(self, x: int) -> TreeViewColumn:
        column_id = self.identify_column(x)
        return self._columns[FIRST_COLUMN if column_id == '#0' else self.column(column_id)['id']]

    def column_named(self, name: str) -> Optional[TreeViewColumn]:
        return self._columns.get(name, None)

    # Node

    def add_node(self, name: str, parent: Optional[TreeViewNode] = None) -> TreeViewNode:
        tags = [NODE_DEFAULT_TAG, name]
        self.insert(parent.name if parent else '', tk.END, name, text='', tags=tags)
        node = self.node_type(self, name, parent=parent)
        self._nodes[name] = node
        return node

    def remove_node(self, name: str):
        self.delete(name)
        del self._nodes[name]

    def clear(self):
        self.delete(*(n.name for n in self))
        self._nodes.clear()

    def node_at(self, x: int, y: int) -> Optional[TreeViewNode]:
        column = self.column_at(x)
        for node in self:
            v = self.bbox(node.name, column=column.name)
            if v:
                nx, ny, width, height = v
                if nx <= x < nx + width and ny <= y < ny + height:
                    return node
        return None

    def node_named(self, name: str) -> Optional[TreeViewNode]:
        return self._nodes.get(name, None)

    def selected(self) -> [TreeViewNode]:
        return [self._nodes[name] for name in self.selection()]


_did_fix_tree_view = False


def _fix_tree_view_colors():
    global _did_fix_tree_view
    if _did_fix_tree_view:
        return
    _did_fix_tree_view = True

    def fixed_map(option):
        # Fix for setting text colour for Tkinter 8.6.9
        # From: https://core.tcl.tk/tk/info/509cafafae
        #
        # Returns the style map for 'option' with any styles starting with
        # ('!disabled', '!selected', ...) filtered out.

        # style.map() returns an empty list for missing options, so this
        # should be future-safe.
        return [elm for elm in style.map('Treeview', query_opt=option) if elm[:2] != ('!disabled', '!selected')]

    style = ttk.Style()
    style.map('Treeview', foreground=fixed_map('foreground'), background=fixed_map('background'))


