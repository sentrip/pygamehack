import tkinter as tk
import tkinter.ttk as ttk
from dataclasses import dataclass
from typing import Optional
import pygamehack as gh
from pygamehack.struct_meta import StructLazyField

from .core.animation import Color, Animation
from .core.tree_view import TreeView, TreeViewColumn, TreeViewNode, FIRST_COLUMN


def ensure_unsigned(v: int, ptr_size: int):
    if v < 0:
        v = -v
        v |= (1 << ((ptr_size * 8) - 1))
    return v


#region VariableNodeConfig
    
@dataclass
class VariableNodeConfig(object):
    can_modify: bool = False
    show_value: bool = False
    show_value_as_hex: bool = False
    show_updates: bool = False

    @staticmethod
    def default(variable, config_modify):
        # TODO: Custom variable configs
        return VariableNodeConfig(
            config_modify.can_modify, 
            not gh.Struct.is_struct(variable), 
            variable.__class__.__name__ == 'ptr', 
            config_modify.show_updates)


#endregion

#region VariableNode

class VariableNode(TreeViewNode):

    #region Public

    def __init__(self, tree: 'VariableTreeView', name: str, parent: Optional['VariableNode']):
        super().__init__(tree, name, parent)
        self.text = name
        self.variable = None
        self.is_root = False
        self.config = VariableNodeConfig()
        self.config_modify = VariableNodeConfig()
        self._did_create_children = False
        self._animation = Animation(
            Color.hsv(0.1, 0.5, 1.0),
            Color.hsv(0.5, 0.5, 1.0),
            duration=0.8,
            setter=lambda c: self.configure(background=c.hex),
            on_complete=lambda: self.configure(background=Color.rgb(1.0, 1.0, 1.0).hex)
        )
        
    @property
    def is_integer(self):
        return self.variable and self.variable.__class__.__name__ in VariableNode._integer_type_names

    @property
    def is_struct(self):
        return gh.Struct.is_struct(self.variable)

    def create_children(self):
        if self._did_create_children:
            return
        
        self._did_create_children = True
        for _, child in gh.Struct.iter_variables(self.variable):
            self.tree.add_variable(child)

    def set_config_property(self, name, value):
        if not getattr(self.config_modify, name, False):
            return

        setattr(self.config, name, value)
        
        if name == 'show_value' or name == 'show_value_as_hex':
            self._update_value()

    def set_variable(self, variable):
        self.set('address', gh.Address.make_string(variable.address.value, variable.address.hack.process.arch))
        if variable.address.type == gh.Address.Type.Dynamic:
            self.set('offset', '' if not variable.address.offsets else gh.Address.make_string(variable.address.offsets[0]))

        self.variable = variable
        self.config_modify = self._get_config_modify()
        self.config = VariableNodeConfig.default(variable, self.config_modify)
        self._update_value()

    @staticmethod
    def get_new_address_name():
        VariableNode._address_name_count += 1
        return f'Address{VariableNode._address_name_count}'

    #endregion

    #region TreeViewNode

    def on_column_update(self, column: TreeViewColumn, node: 'TreeViewNode'):
        if self.config.show_updates and column.name == 'value':
            Animation.animate(self.tree, self._animation)

    #endregion

    #region Private

    def _get_config_modify(self):
        config = VariableNodeConfig()
        
        if self.is_struct:
            config.show_updates = True
        else:
            config = VariableNodeConfig(True, True, True, True)
        
        if not self.is_integer or self.variable.__class__.__name__ == 'ptr':
            config.show_value_as_hex = False

        return config

    def _update_value(self):
        if not self.config.can_modify:
            return

        elif not self.config.show_value:
            self.set('value', '')

        else:
            variable_value = self.variable.read()
            value = str(variable_value)

            if self.is_integer and self.config.show_value_as_hex:
                unsigned_value = ensure_unsigned(variable_value, self.variable.address.hack.process.ptr_size)
                value = gh.Address.make_string(unsigned_value)
            
            self.set('value', value)

    _address_name_count = 0
    
    _integer_type_names = {
        'i8', 'i16', 'i32', 'i64',
        'u8', 'u16', 'u32', 'u64',
        'int', 'uint', 'ptr', 'usize'
    }

    #endregion


#endregion

#region VariableTreeView

class VariableTreeView(TreeView):
    
    #region Public

    def __init__(self, master):
        super().__init__(master)
        self.struct = master.struct
        self.can_right_click = True
        self.node_type = VariableNode
        self.variable_to_node = {}

        self.setup_columns()
        
        self._thread = None
        def _set():
            self.struct.flag = 1
            if self._thread is None:
                import threading
                def run():
                    while True:
                        self.update()
                self._thread = threading.Thread(target=run, daemon=True)
                self._thread.start()

        self.bind('<Key-Delete>', self._remove_selected_variables)
        self.bind('<Key-Insert>', lambda e: self.add_variable(self.struct))
        self.bind('<Key-Return>', lambda e: _set())

    def add_variable(self, variable):
        did_expand = False
        for name, child in gh.Struct.iter_variables(variable):
            if isinstance(child, StructLazyField):
                getattr(variable, name)
                did_expand = True

        if not did_expand and variable in self.variable_to_node:
            return

        for name, child, parent in gh.Struct.walk(variable):
            if isinstance(child, StructLazyField) or self.variable_to_node.get(child, None) is not None:
                continue

            name = child.address.name or name or VariableNode.get_new_address_name()
            parent_node = self.variable_to_node.get(parent, None)
            child_node = self.add_node(name, parent_node)
            child_node.is_root = parent_node is None
            child_node.set_variable(child)
            self.variable_to_node[child] = child_node

    def remove_variable(self, variable):
        node = self.variable_to_node.get(variable, None)
        if node is None or not node.is_root:
            return

        for name, child, parent in gh.Struct.walk(variable):
            if child in self.variable_to_node:
                del self.variable_to_node[child]

        self.remove_node(node.name)

    def update(self):
        for node in self.variable_to_node.values():
            node._update_value()

    #endregion

    #region TreeView
    
    def on_select(self):
        pass

    def on_open_node(self, node: VariableNode):
        if node:
            node.create_children()
    
    def on_close_node(self, node: VariableNode):
        pass

    def on_double_click(self, column: TreeViewColumn, node: VariableNode):
        if column == 'value':
            print('edit value')

    def on_right_click(self, column: TreeViewColumn, node: 'TreeViewNode'):
        if self._is_right_clicked_node_uniquely_selected():
            self.selection_set(node.name)
        self._update_right_click_menu()

    #endregion

    #region Setup

    def setup_columns(self):
        self.add_columns(('address', 'Address'), ('offset', 'Offset'), ('value', 'Value'))

        self.column_named(FIRST_COLUMN)\
            .configure(width=375, minwidth=375, stretch=tk.NO)

        self.column_named('address')\
            .configure(width=150, minwidth=150, stretch=tk.NO)

        self.column_named('offset') \
            .configure(width=75, minwidth=75, stretch=tk.NO)

        self.column_named('value') \
            .configure(width=450, minwidth=200, stretch=tk.YES)

    def create_right_click_menu(self):
        requested_names = set(VariableTreeView._label_names)
        right_clicked_node_is_unique = self.right_clicked_node and self._is_right_clicked_node_uniquely_selected()

        if right_clicked_node_is_unique:
            if self.right_clicked_node.is_struct:
                requested_names = ['show_updates']
            elif not self.right_clicked_node.is_integer:
                requested_names = ['can_modify', 'show_value', 'show_updates']

        # NOTE: For some reason when you create a lambda inline inside of the loop, the right clicking
        # only ever detects the final command in the list. This is probably because of some string reference
        # counting nonsense that tkinter is not doing properly.
        create_right_click_lambda = lambda n, v: lambda: self._set_config_property_selected_nodes(n, v)

        for i, name in enumerate(VariableTreeView._label_names):
            if name not in requested_names:
                continue
            
            for j in range(2):
                value = bool(1 - j)
                
                if right_clicked_node_is_unique and value == getattr(self.right_clicked_node.config, name):
                    continue

                self.right_click_menu.add_command(
                    label=VariableTreeView._labels[i * 2 + j],
                    # This should be identical and should work, but it doesnt...
                    # command=lambda: self._set_config_property_selected_nodes(name, v))
                    command=create_right_click_lambda(name, value))

    #endregion

    #region Private

    def _is_right_clicked_node_uniquely_selected(self):
        if self.right_clicked_node is None:
            return True
        
        selected = self.selected()
        if len(selected) > 1 and self.right_clicked_node in selected:
            return False
        
        return True
        
    def _remove_selected_variables(self, event=None):
        selected = self.selected()
        for node in selected:
            self.remove_variable(node.variable)

    def _set_config_property_selected_nodes(self, property_name, value):
        selected = self.selected()

        if self.right_clicked_node in selected:
            for node in selected:
                node.set_config_property(property_name, value)
        
        elif self.right_clicked_node:
            self.right_clicked_node.set_config_property(property_name, value)

    def _update_right_click_menu(self):
        self.right_click_menu.delete(0, tk.END)
        self.create_right_click_menu()

    _label_names = [
        'can_modify', 'show_value', 'show_value_as_hex', 'show_updates'
    ]

    _labels = [
        'Enable modification  ',            'Disable modification   ',
        'Show value                   (?)', 'Hide value                    (?)',
        'Display as hex              (?)',  'Display as decimal      (?)',
        'Enable animation        (?)',      'Disable animation       (?)'
    ]
    
    #endregion

#endregion
