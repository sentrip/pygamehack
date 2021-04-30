import tkinter as tk
import tkinter.ttk as ttk
from typing import Optional, Union
import pygamehack as gh

from .core.tree_view import TreeView, TreeViewColumn, TreeViewNode, FIRST_COLUMN


#region Tree-Based

BACKGROUND = 'white'
HIGHLIGHT = 'light blue'

#region TreeSelectManager

class TreeSelectManager(object):
    def __init__(self, tree):
        self.tree = tree
        self.selection = []
        self._moving_reversed = False

    def clear(self):
        self._moving_reversed = False
        for other in self.selection:
            other._view_values.deselect()
        self.selection.clear()

    def select(self, node):
        self.clear()
        node._view_values.select()
        self.selection.append(node)

    def select_multiple(self, nodes):
        self.clear()
        for node in nodes:
            node._view_values.select()
            self.selection.append(node)

    def move_selection_down(self):
        if not self.selection:
            return
        
        begin = self.selection[0]

        if len(self.selection) > 1:
            self.select(begin)

        can_move_into_child = begin.has_children and begin.expanded

        if can_move_into_child:
            self.select(begin.first_child)
            return
        
        next_sibling = begin.next_sibling
        if next_sibling:
            self.select(next_sibling)

    def move_selection_up(self):
        if not self.selection:
            return
        
        begin = self.selection[0]

        if len(self.selection) > 1:
            self.select(begin)

        previous_sibling = begin.previous_sibling
        if previous_sibling:
            self.select(previous_sibling)
            return

        if begin.parent != self and isinstance(begin.parent, TreeNode):
            self.select(begin.parent)

    def add_selection_down(self):
        if self.selection:
            # Remove from selection downwards
            if self._moving_reversed:
                self.selection[0]._view_values.deselect()
                self.selection.pop(0)
                # Change direction when a single node is selected
                if len(self.selection) == 1:
                    self._moving_reversed = False
            # Add to selection downwards
            else:
                next_node = self.selection[-1].first_child or self.selection[-1].next_sibling
                if next_node:
                    next_node._view_values.select()
                    self.selection.append(next_node)

    def add_selection_up(self):
        if self.selection:
            # Add to selection upwards
            if self._moving_reversed:
                previous_node = self.selection[0].previous_sibling or self.selection[0].parent
                if previous_node and isinstance(previous_node, TreeNode):
                    previous_node._view_values.select()
                    self.selection.insert(0, previous_node)
            # Remove from selection upwards
            elif len(self.selection) > 1:
                self.selection[-1]._view_values.deselect()
                self.selection.pop(-1)
            # Change direction when a single node is selected
            else:
                self._moving_reversed = True
                self.add_selection_up()

    def expand(self):
        if self.selection:
            begin = self.selection[0]
            
            if len(self.selection) > 1:
                self.select(begin)

            if begin.has_children and not begin.expanded:
                begin.expand()
            else:
                self.move_selection_down()

    def collapse(self):
        if self.selection:
            begin = self.selection[0]
            
            if len(self.selection) > 1:
                self.select(begin)

            if begin.has_children and begin.expanded:
                begin.collapse()
            else:
                self.move_selection_up()

#endregion

#region TreeColumn

class TreeColumn(object):
    def __init__(self, name, title):
        self.name = name
        self.title = title
        self.width = 100
        self.min_width = 100

#endregion

#region TreeNodeValues

class TreeNodeValues(tk.Frame):

    #region Public

    def __init__(self, node, **kwargs):
        super().__init__(node, bg=BACKGROUND)

        self.node = node
        self.tree = node.tree
        self.level = node._level
        self.expand_button_variable = tk.StringVar(value='')
        self.value_variables = [tk.StringVar('') for _ in range(len(self.tree.columns))]

        self.tree_label_frame = tk.Frame(self, bg=BACKGROUND)
        self.value_labels_frame = tk.Frame(self, bg=BACKGROUND)
        self.tree_label_sub_frame = tk.Frame(self.tree_label_frame, bg=BACKGROUND)

        self.tree_label = tk.Label(self.tree_label_sub_frame, textvariable=self.value_variables[0])
        
        self.value_labels = [tk.Label(self.value_labels_frame, textvariable=self.value_variables[i]) 
                            for i in range(1, len(self.tree.columns))]
        
        self.expand_button = tk.Button(self.tree_label_sub_frame, bg=BACKGROUND, relief=tk.FLAT, 
                                        textvariable=self.expand_button_variable, 
                                        command=self.node.expand_toggle)

        self._setup_view()
        self._setup_events()
        self.deselect()

    @property
    def fields(self):
        yield self.tree_label_frame
        yield self.tree_label_sub_frame
        yield self.expand_button
        yield self.tree_label
        yield self.value_labels_frame
        for v in self.value_labels:
            yield v
    
    def bind(self, event, handler):
        for field in self.fields:
            field.bind(event, handler)

    def expand(self):
        self.expand_button_variable.set('' if not self.node._children else '-')

    def collapse(self):
        self.expand_button_variable.set('' if not self.node._children else '+')

    def deselect(self):
        for field in self.fields:
            field.configure(bg=BACKGROUND)

    def select(self):
        for field in self.fields:
            field.configure(bg=HIGHLIGHT)

    def get_value(self, index):
        return self.value_variables[index].get()
    
    def set_value(self, index, value):
        self.value_variables[index].set(value)

    #endregion

    #region Private

    def _setup_view(self):
        # Grid config
        self.columnconfigure(0, minsize=self.tree.columns[0].min_width)
        self.columnconfigure(1, minsize=sum(i.min_width for i in self.tree.columns[1:]))
        for i in range(len(self.value_labels)):
            self.value_labels_frame.columnconfigure(i, minsize=self.tree.columns[i + 1].min_width)

        # Tree label
        self.expand_button.pack(side=tk.LEFT, fill=tk.BOTH)
        self.tree_label.pack(side=tk.LEFT, fill=tk.BOTH)
        self.tree_label_sub_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=self.level * 10)
        self.tree_label_frame.grid(column=0, row=0, sticky='news')
        
        # Values
        for i, value in enumerate(self.value_labels):
            value.grid(column=i, row=0, sticky='news')
            self.value_labels_frame.columnconfigure(i, minsize=self.tree.columns[i + 1].min_width)
        self.value_labels_frame.grid(column=1, row=0, sticky='news')

    def _setup_events(self):
        self.bind('<Down>', self.tree._on_down)
        self.bind('<Up>', self.tree._on_up)
        self.bind('<Left>', self.tree._on_left)
        self.bind('<Right>', self.tree._on_right)
        self.bind('<Shift-Down>', self.tree._on_shift_and_down)
        self.bind('<Shift-Up>', self.tree._on_shift_and_up)
        self.bind('<Double-Button-1>', self._on_double_left_click)
        for field in self.fields:
            field.bind('<Button-1>', lambda e: self._on_left_click(field, e), '+')
        for field in self.fields:
            field.bind('<Button-3>', lambda e: self._on_right_click(field, e), '+')

    def _on_left_click(self, field, event):
        field.focus_set()
        return self.tree._on_left_click(self.node)

    def _on_right_click(self, field, event):
        field.focus_set()
        return self.tree._on_right_click(self.node)

    def _on_double_left_click(self, event):
        return self.tree._on_double_left_click(self.node)

    def _on_update_children(self):
        self.expand_button_variable.set('' if not self.node._children else ('-' if self.node._expanded else '+'))
        self.expand_button.configure(state=tk.NORMAL if self.node._children else tk.DISABLED)
    
    #endregion

#endregion

#region TreeNodeBase

class TreeNodeBase(tk.Frame):
    def __init__(self, master, parent, **kwargs):
        self._level = kwargs.pop('level', 0)
        self._has_values = kwargs.pop('has_values', False)
        
        super().__init__(parent._children_frame if parent else master._root_frame, bg=BACKGROUND)
        
        self.tree = parent.tree if parent else master.tree
        
        self._children = []
        self._children_frame = tk.Frame(self, bg=BACKGROUND)
        self._children_frame_added = False
    
    def add_node(self) -> 'TreeNode':
        if not self._children_frame_added:
            self.columnconfigure(0, minsize=sum(i.min_width for i in self.tree.columns))
            self._children_frame.grid(column=0, row=int(self._has_values), sticky='news')
            
        index = len(self._children)
        child = TreeNode(self, index=index, level=self._level + 1, has_values=True)
        child.grid(column=0, row=index, sticky='news')
        self._children.append(child)
        self._on_update_children()
        return child

    def _on_update_children(self):
        pass

#endregion

#region TreeNode

class TreeNode(TreeNodeBase):
    def __init__(self, parent, **kwargs):
        self._index = kwargs.pop('index', 0)
        
        super().__init__(parent, parent, **kwargs)
        
        self.parent = parent
        self.tree = parent.tree

        self._expanded = True
        self._view_values = TreeNodeValues(self)

        self._view_values.grid(column=0, row=0, sticky='news')
    
    def collapse(self):
        self._expanded = False
        self._view_values.collapse()
        if self._children:
            self._children_frame.grid_remove()

    def expand(self):
        self._expanded = True
        self._view_values.expand()
        if self._children:
            self._children_frame.grid(column=0, row=1, sticky='ew')

    def expand_toggle(self):
        self.collapse() if self._expanded else self.expand()

    def collapse_children(self, recursive=False):
        for child in self._children:
            child.collapse()
            if recursive:
                child.collapse_children(recursive=True)

    def expand_children(self, recursive=False):
        for child in self._children:
            child.expand()
            if recursive:
                child.expand_children(recursive=True)

    def expand_toggle_children(self, recursive=False):
        for child in self._children:
            child.collapse() if child._expanded else child.expand()
            if recursive:
                child.expand_toggle_children(recursive=True)

    def get(self, column: str) -> str:
        for i, c in enumerate(self.tree.columns):
            if column == c.name:
                return self._view_values.get(i)
        raise KeyError(f'Unknown column: {column}')

    def set(self, column: str, value: str):
        for i, c in enumerate(self.tree.columns):
            if column == c.name:
                self._view_values.set_value(i, value)
                return
        raise KeyError(f'Unknown column: {column}')

    def set_many(self, *column_value_pairs):
        for column, value in column_value_pairs:
            self.set(column, value)

    @property
    def expanded(self):
        return self._expanded

    @property
    def has_children(self):
        return bool(self._children)

    @property
    def first_child(self):
        if self._children:
            return self._children[0]
        return None

    @property
    def last_child(self):
        if self._children:
            return self._children[-1]
        return None

    @property
    def siblings(self):
        if self.parent:
            for node in self.parent._children:
                if node != self:
                    yield node
        return None

    @property
    def previous_sibling(self):
        if self.parent and self._index > 0:
            return self.parent._children[self._index - 1]
        return None

    @property
    def next_sibling(self):
        if self.parent and (self._index + 1) < len(self.parent._children):
            return self.parent._children[self._index + 1]
        return None

    def _on_update_children(self):
        self._view_values._on_update_children()

#endregion

#region Tree

class Tree(tk.Frame):

    #region Public

    def __init__(self, master):
        super().__init__(master, None)

        self.tree = self
        self.columns = []
        self._root_frame = tk.Frame(self, bg=BACKGROUND)
        self._root_frame.tree = self
        self.root = TreeNodeBase(self, None)
        self._scrollbar = tk.Scrollbar(self, command=lambda *a: self._on_scroll(*a))
        self._select_manager = TreeSelectManager(self)
        
        self.root.place(x=0, y=0, relwidth=1, relheight=1, anchor=tk.NW)
        self._root_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._scrollbar.pack(side=tk.LEFT, fill=tk.Y)

    def add_column(self, name: str, title: str) -> TreeColumn:
        column = TreeColumn(name, title)
        self.columns.append(column)
        return column

    def add_node(self) -> 'TreeNode':
        return self.root.add_node()

    #endregion

    #region Events

    def on_left_click(self, node):
        pass
    
    def on_right_click(self, node):
        pass

    def on_double_left_click(self, node):
        pass

    #endregion

    #region Private

    def _on_up(self, event=None):
        self._select_manager.move_selection_up()
    
    def _on_down(self, event=None):
        self._select_manager.move_selection_down()

    def _on_left(self, event=None):
        self._select_manager.collapse()
    
    def _on_right(self, event=None):
        self._select_manager.expand()

    def _on_shift_and_down(self, event=None):
        self._select_manager.add_selection_down()
    
    def _on_shift_and_up(self, event=None):
        self._select_manager.add_selection_up()

    def _on_left_click(self, node):
        self._select_manager.select(node)
        self.on_left_click(node)
    
    def _on_right_click(self, node):
        self._select_manager.select(node)
        self.on_right_click(node)

    def _on_double_left_click(self, node):
        node.expand_toggle()
        self.on_double_left_click(node)
    
    def _on_scroll(self, command, *values):
        height = self.root.winfo_height()
        if command == 'moveto':
            fraction = float(values[0])
            self.root.place(x=0, y=-fraction * height, relwidth=1, relheight=1, anchor=tk.NW)
            self._scrollbar.set(fraction, fraction + 0.1)
        elif command == 'scroll':
            distance, units = int(values[0]), values[1]
            if units == 'units':
                pass
            elif units == 'pages':
                pass

    #endregion

#endregion

#region ClassView

class ClassView(Tree):
    def __init__(self, master):
        super().__init__(master)

        # debug
        self.add_column('offset', 'Offset').min_width = 300
        self.add_column('address', 'Address').min_width = 150
        self.add_column('bytes', 'Bytes')
        self.add_column('hex', 'Hex').min_width = 200
        self.add_column('value_int', 'Value')
        self.add_column('value_float', '')

        n0 = self.add_node()
        n0.set_many(('offset', '0000'), ('address', '00000000'), ('bytes', 'a  .  .  .  .  .  .  .'), ('hex', '00 00 00 00 00 00 00 00'), ('value_int', '0'), ('value_float', '0.0000'))
        n1 = n0.add_node()
        n1.set_many(('offset', '0000'), ('address', '00000000'), ('bytes', 'b  .  .  .  .  .  .  .'), ('hex', '00 00 00 00 00 00 00 00'), ('value_int', '0'), ('value_float', '0.0000'))
        n2 = n0.add_node()
        n2.set_many(('offset', '0004'), ('address', '00000004'), ('bytes', 'c  .  .  .  .  .  .  .'), ('hex', '00 00 00 00 00 00 00 00'), ('value_int', '0'), ('value_float', '0.0000'))
        n3 = n2.add_node()
        n3.set_many(('offset', '0000'), ('address', '00000004'), ('bytes', 'd  .  .  .  .  .  .  .'), ('hex', '00 00 00 00 00 00 00 00'), ('value_int', '0'), ('value_float', '0.0000'))
        n4 = n3.add_node()
        n4.set_many(('offset', '0000'), ('address', '00000004'), ('bytes', 'e  .  .  .  .  .  .  .'), ('hex', '00 00 00 00 00 00 00 00'), ('value_int', '0'), ('value_float', '0.0000'))
        for i in range(100):
            n = n3.add_node()
            n.set_many(('offset', '000' + str((i + 1))), ('address', '0000000' + str((i + 1))), ('bytes', chr(i + 20) + '  .  .  .  .  .  .  .'), ('hex', '00 00 00 00 00 00 00 00'), ('value_int', '0'), ('value_float', '0.0000'))

    #region Tree

    def on_left_click(self, node):
        pass
    
    def on_right_click(self, node):
        pass

    def on_double_left_click(self, node):
        pass

    #endregion


#endregion

#endregion


#region TreeView-Based

#region ClassInstance

class ClassInstance(object):

    def __init__(self, hack, parent, offset, node_type):
        self.hack = hack
        self.name = ''
        self.address = 0
        self.size = ClassInstance.get_type_size(node_type)
        self.type = node_type
        self.parent = parent
        self.offset_in_parent = offset
        self.children = []
        self.buffer = None
        self.set_offset_in_parent(offset)

    def add_bytes(self, n_bytes):
        self.size += n_bytes
        self._resize_buffer(n_bytes)

    def remove_bytes(self, n_bytes):
        for i in range(len(self.children) - 1, -1, -1):
            if child.offset + child.size < self.size - n_bytes:
                self.children = self.children[:i+1]
                break
        self.size -= n_bytes

    def insert_bytes(self, offset, n_bytes):
        offsets_to_update = []
        for child in self.children:
            if child.offset_in_parent >= offset:
                child.set_offset_in_parent(child.offset_in_parent + n_bytes)
        self.size += n_bytes
        self._resize_buffer(n_bytes)

    def recalculate_address(self):
        if self.parent:
            self.parent.recalculate_address()
            self.address = self.parent.address + self.offset_in_parent

    def recalculate_child_addresses(self, recursive=True):
        for child in self.children:
            child.address = self.address + child.offset_in_parent
            if recursive:
                child.recalculate_child_addresses(recursive=True)

    def set_offset_in_parent(self, offset):
        buffer_type = gh.Buffer if True else gh.Buffer # TODO: Pointer to buffers
        if self.parent:
            self.buffer = buffer_type(self.parent.buffer, self.offset_in_parent, ClassInstance.get_buffer_size(self.size))
        else:
            self.buffer = buffer_type(self.hack, ClassInstance.get_buffer_size(self.size))

        self.offset_in_parent = offset

        for child in self.children:
            child.set_offset_in_parent(child.offset_in_parent)

    def set_type(self, offset, node_type):
        for i, node in enumerate(self.children):
            if node.offset == offset:
                self._set_type(i, node, node_type)
                return
            elif node.offset > offset:
                self._insert_child(i, offset, node_type)
                return

    @staticmethod 
    def get_type_size(cls):
        # TODO: get size of type
        return 8

    @staticmethod
    def get_buffer_size(size):
        return size * 2

    def _insert_child(self, index, offset, node_type):
        child = ClassInstance(self.hack, self, offset, node_type)
        self.children.insert(index, child)
        for i in range(index + 1, len(self.children)):
            self.children[i].set_offset_in_parent(self.children[i].offset + child.size)
    
    def _resize_buffer(self, n_bytes):
        if self.size + n_bytes >= self.buffer.size:
            self.buffer.resize(ClassInstance.get_buffer_size(self.size))
            self.set_offset_in_parent(self.offset_in_parent)

    def _set_type(self, index, node, node_type):
        node.type = node_type
        previous_size = node.size
        new_size = ClassInstance.get_type_size(node_type)
        node.size = new_size
        if previous_size != new_size:
            # grow - consume bytes / (offset bytes?)
            if previous_size < new_size:
                pass
            # shrink - insert bytes to fit
            else:
                pass
    

#endregion

#region ClassNode

class ClassNode(TreeViewNode):

    #region Public

    def __init__(self, tree: 'ClassTreeView', name: str, parent: Optional['ClassNode']):
        super().__init__(tree, name, parent)
        self.instance = None
        self.text = '00000'
        self.set('address', '00000000')
        self.set('type', '')
        self.set('name', '')
        self.set('bytes', 'a  .  .  .  .  .  .  .')
        self.set('hex', '00 00 00 00 00 00 00 00')
        self.set('value_int', '0')
        self.set('value_float', '0.0000')

    def set_address(self, address, offset):
        self.instance = ClassInstance(self.tree.hack, self.parent.instance if self.parent else None, offset, None)
        self.instance.address = address
        self.instance.recalculate_child_addresses(recursive=True)
        self.instance.buffer.read_from(self.instance.address)
        if True:
            self._set_basic_values()        
        
    #endregion

    #region TreeViewNode

    def on_column_update(self, column: TreeViewColumn, node: 'TreeViewNode'):
        pass

    #endregion

    #region Private

    def _set_basic_values(self):
        self.text = str(self.instance.offset_in_parent)
        self.set('address', gh.Address.make_string(self.instance.address, self.tree.hack.process.arch)[2:])
        raw_bytes = self.instance.buffer.read_bytes(0, 8)
        byte_string = ''
        hex_string = ''
        for i, v in enumerate(raw_bytes):
            if i > 0:
                byte_string += '  '
                hex_string += ' '
            hex_string += '%X' % v
            if v != 0:
                byte_string += chr(v)
            else:
                byte_string += '.'

        self.set('bytes', byte_string)
        self.set('hex', hex_string)
        self.set('value_int', self.instance.buffer.read_i64(0))
        self.set('value_float', self.instance.buffer.read_double(0))

    #endregion

#endregion

#region ClassTreeView

class ClassTreeView(TreeView):
    
    #region Public

    def __init__(self, master):
        self.frame = tk.Frame(master)
        super().__init__(self.frame)

        self.default_node_size = 8

        self.can_right_click = True
        self.node_type = ClassNode
        self._scrollbar = tk.Scrollbar(self.frame, orient="vertical", command=self.yview)

        self.setup_columns()
        self.setup_scrollbar()
        self.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.hack = master.hack
        self.instance = ClassInstance(self.hack, None, 0, None)
        
        node = self.add_node('root')
        node.set_address(master.root_address.value, 0)

    #endregion

    #region TreeView
    
    def on_select(self):
        pass

    def on_open_node(self, node: ClassNode):
        pass
    
    def on_close_node(self, node: ClassNode):
        pass

    def on_double_click(self, column: TreeViewColumn, node: ClassNode):
        pass

    def on_right_click(self, column: TreeViewColumn, node: 'TreeViewNode'):
        self._update_right_click_menu()

    #endregion

    #region Setup

    def setup_columns(self):
        self.add_columns(('address', 'Address'),
                        ('type', 'Type'),
                        ('name', 'Name'),
                        ('bytes', 'Bytes'),
                        ('hex', 'Hex'),
                        ('value_int', 'Value'),
                        ('value_float', ''))

        self.column_named(FIRST_COLUMN)\
            .configure_header(text='Offset')

        self.column_named(FIRST_COLUMN)\
            .configure(width=350, minwidth=350, stretch=tk.NO)

        self.column_named('address')\
            .configure(width=150, minwidth=150, stretch=tk.NO)

        self.column_named('type')\
            .configure(width=150, minwidth=150, stretch=tk.NO)

        self.column_named('name')\
            .configure(width=150, minwidth=150, stretch=tk.NO)

        self.column_named('bytes') \
            .configure(width=100, minwidth=100, stretch=tk.NO)

        self.column_named('hex') \
            .configure(width=150, minwidth=150, stretch=tk.NO)

        self.column_named('value_int') \
            .configure(width=100, minwidth=100, stretch=tk.NO)

        self.column_named('value_float') \
            .configure(width=100, minwidth=100, stretch=tk.YES)

    def setup_scrollbar(self):
        self.configure(yscrollcommand=self._scrollbar.set)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_right_click_menu(self):
        requested_names = set(ClassTreeView._right_click_commands)
        right_clicked_node_is_unique = False

        # NOTE: For some reason when you create a lambda inline inside of the loop, the right clicking
        # only ever detects the final command in the list. This is probably because of some string reference
        # counting nonsense that tkinter is not doing properly.
        create_right_click_lambda = lambda n: lambda: self._do_right_click_command(n)

        for i, name in enumerate(ClassTreeView._right_click_commands):
            if name not in requested_names:
                continue
            
            self.right_click_menu.add_command(
                label=ClassTreeView._right_click_command_labels[name],
                # This should be identical and should work, but it doesnt...
                # command=lambda: self._do_right_click_command(name))
                command=create_right_click_lambda(name))

    #endregion

    #region Private
    
    def _do_right_click_command(self, cmd):
        clicked_node = self.right_clicked_node or self
        parent_node = (self.right_clicked_node.parent if self.right_clicked_node else self) or self
        if cmd == 'add_64':
            for i in range(0,64, self.default_node_size):
                self.instance.add_bytes(self.default_node_size)
                node = self.add_node('node' + str(i + parent_node.instance.size - self.default_node_size))
                node.set_address(parent_node.instance.address, parent_node.instance.size - self.default_node_size)

        elif cmd == 'remove':
            for name in self.selection():
                self.remove_node(name)


    def _update_right_click_menu(self):
        self.right_click_menu.delete(0, tk.END)
        self.create_right_click_menu()

    _right_click_commands = [
        'add_64',
        'remove'
    ]

    _right_click_command_labels = {
        'add_64': 'Add 64 bytes...',
        'remove': 'Remove',
    }

    #endregion

#endregion

ClassView = ClassTreeView

#endregion
