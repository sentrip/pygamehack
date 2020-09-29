from typing import Any, Optional

import tkinter as tk
import tkinter.ttk as ttk
from tkinter.simpledialog import Dialog

import pygamehack as gh
from pygamehack_utils.debug_view import DebugViewFactory, DebugView
from .core.animation import Color, Animation
from .core.tree_view import TreeView, TreeViewColumn, TreeViewNode, FIRST_COLUMN, NODE_DEFAULT_TAG


def _toggle(node, property_name):
    setattr(node, property_name, not getattr(node, property_name))


class VariableNode(TreeViewNode):

    def __init__(self, tree: 'VariableTreeView', name: str, parent: Optional['VariableNode']):
        super().__init__(tree, name, parent)
        self.can_modify = True
        self.show_value = True
        self.show_value_as_hex = False
        self.show_updates = True
        self.value_type = gh.uint32
        self.variable = None
        self.property_name = ''
        self.ptr_size = 0

        self.debug_view = None
        self._animation = Animation(
            Color.hsv(0.1, 0.5, 1.0),
            Color.hsv(0.5, 0.5, 1.0),
            duration=0.8,
            setter=lambda c: self.configure(background=c.hex),
            on_complete=lambda: self.configure(background=Color.rgb(1.0, 1.0, 1.0).hex)
        )

    def set_variable(self, address_or_variable: Any, t: Optional[type] = None):
        # Update variable
        vt = t or self.value_type
        self.variable = vt(address_or_variable) if isinstance(address_or_variable, gh.Address) else address_or_variable
        self.value_type = self.variable.__class__
        # print(self.variable, self.value_type)

        # Update config for variable
        config = self.variable.debug_config()
        self.can_modify, self.show_value, self.show_value_as_hex, self.show_updates = \
            config.can_modify, config.show_value, config.show_value_as_hex, config.show_updates

        # Set property name
        self.property_name = self.variable.address.name.split('/')[-1].split('.')[-1]
        self.ptr_size = self.variable.address.hack.ptr_size

    def update(self):
        self.set('address', f'{self.variable.debug_address():0{2 * self.ptr_size}X}')

        if self.show_value:
            self.set('value', self.variable.debug_string(self.show_value_as_hex))
        elif self.get('value'):
            self.set('value', '')

    def on_column_update(self, column: TreeViewColumn, node: 'TreeViewNode'):
        if self.tree.show_updates and self.show_updates and column.name == 'value':
            Animation.animate(self.tree, self._animation)


class VariableTreeView(TreeView):
    def __init__(self, master):
        super().__init__(master)
        self.show_updates = True

        self.node_type = VariableNode

        self.can_right_click = True
        # We need a unique lambda for each command when done in a for loop everything breaks
        self.right_click_menu.add_command(label=VariableTreeView._labels['can_modify'][0],
                                          command=lambda: self._toggle_node('can_modify'))
        self.right_click_menu.add_command(label=VariableTreeView._labels['show_value'][0],
                                          command=lambda: self._toggle_node('show_value'))
        self.right_click_menu.add_command(label=VariableTreeView._labels['show_value_as_hex'][0],
                                          command=lambda: self._toggle_node('show_value_as_hex'))
        self.right_click_menu.add_command(label=VariableTreeView._labels['show_updates'][0],
                                          command=lambda: self._toggle_node('show_updates'))

        self.add_columns(('address', 'Address'), ('offset', 'Offset'), ('value', 'Value'))

        self.column_named(FIRST_COLUMN)\
            .configure(width=270, minwidth=270, stretch=tk.NO)

        self.column_named('address')\
            .configure(width=120, minwidth=120, stretch=tk.NO)

        self.column_named('offset') \
            .configure(width=60, minwidth=60, stretch=tk.NO)

        self.column_named('value') \
            .configure(width=400, minwidth=200, stretch=tk.YES)

    def add_variable(self, address_or_variable: Any) -> VariableNode:
        address = address_or_variable if isinstance(address_or_variable, gh.Address) else address_or_variable.address
        parent = self.node_named(address.previous.name) if address.previous else None
        node = self.add_node(address.name, parent)  # type: VariableNode
        node.set_variable(address_or_variable)
        node.text = node.property_name

        if address.offsets:
            off = address.offsets[-2] if not address.offsets[-1] and len(address.offsets) > 1 else address.offsets[-1]
            node.set('offset', f'0x{off:X}')

        return node

    def update_nodes(self):
        for node in self:
            node.update()

    def on_double_click(self, column: TreeViewColumn, node: VariableNode):
        if column.name == 'address':
            AddressPopup(self, node)
        elif column.name == 'value' and node.show_value:
            popup = VariablePopup(self, node)
            if popup.did_update:
                node.variable.write(popup.value)

    def on_right_click(self, column: TreeViewColumn, node: 'TreeViewNode'):
        for i, (name, labels) in enumerate(VariableTreeView._labels.items()):  # Dicts should be sorted now right?
            self.right_click_menu.entryconfigure(i, label=labels[int(getattr(node, name))])

    def _toggle_node(self, property_name):
        if property_name == 'show_value' or property_name == 'show_value_as_hex':
            previous_show_updates = self.right_clicked_node.show_updates
            self.right_clicked_node.show_updates = False
            _toggle(self.right_clicked_node, property_name)
            self.right_clicked_node.update()
            self.right_clicked_node.show_updates = previous_show_updates
        else:
            _toggle(self.right_clicked_node, property_name)

    _labels = {
        'can_modify':        ['Enable modification  ', 'Disable modification   '],
        'show_value':        ['Show value                   (L)', 'Hide value                    (L)'],
        'show_value_as_hex': ['Display as hex              (H)', 'Display as decimal      (H)'],
        'show_updates':      ['Enable animation        (U)', 'Disable animation       (U)']
    }


# region Dialog

class VariableNodeDialog(Dialog):

    def __init__(self, master, node: VariableNode, column_name: str, title: str):
        self.node = node
        self.column_name = column_name
        self.value = node.get(column_name)
        super().__init__(master, title=title)

    def header(self, master):
        label = ttk.Label(master, text=self.node.property_name)
        label.pack(side=tk.TOP, fill=tk.X, padx=4, expand=True)

        label = ttk.Label(master, text=self.column_name + ':')
        label.pack(side=tk.TOP, fill=tk.X, padx=4, expand=True)

    def body(self, master):
        self.header(master)

        entry = tk.Text(master, width=16, height=1)
        entry.insert(tk.INSERT, self.value)
        entry.configure(state=tk.DISABLED)

        entry.pack(side=tk.TOP, fill=tk.X, padx=4, pady=4, expand=True)

        entry.bind('<Escape>', self.cancel)
        entry.bind('<Return>', self.ok)

        entry.tag_add(tk.SEL, "1.0", tk.END)
        entry.mark_set(tk.INSERT, "1.0")
        entry.see(tk.INSERT)
        entry.focus_set()

        return entry

    def buttonbox(self):
        frame = tk.Frame(self)
        ok_button = ttk.Button(frame, text="OK", command=self.ok)
        ok_button.pack(side=tk.BOTTOM, expand=True)
        frame.pack()


class AddressPopup(VariableNodeDialog):

    def __init__(self, master, node: VariableNode):
        super().__init__(master, node, 'address', 'Address')


class VariablePopup(VariableNodeDialog):

    def __init__(self, master, node: VariableNode):
        self.did_update = False
        self._view = None
        self._view_factory = node.debug_view or getattr(
            node.variable, 'debug_view', lambda: DebugViewFactoryBasic(node, self))()
        super().__init__(master, node, 'value', 'Value')

    def body(self, master):
        self._view = self._view_factory.create_view(master)
        return self._view

    def apply(self):
        self.value = self._view_factory.get_value(self._view) or self.value
        self.did_update = True

    def validate(self):
        return self._view_factory.validate_value(self._view)


class DebugViewFactoryBasic(DebugViewFactory):

    def __init__(self, node: VariableNode, popup: VariableNodeDialog):
        self.entry = None
        self.popup = popup
        self.can_modify = node.can_modify
        self.is_integer = isinstance(node.variable.read(), int)
        self.is_float = isinstance(node.variable.read(), float)

    def create_view(self, master: tk.Frame) -> DebugView:
        self.entry = VariableNodeDialog.body(self.popup, master)
        if self.can_modify:
            self.entry.configure(state=tk.NORMAL)
        return self.entry

    def get_value(self, view: DebugView) -> Any:
        value = self.entry.get(1.0, tk.END).strip().strip('\n')
        return int(value) if self.is_integer else (float(value) if self.is_float else value)

    def validate_value(self, view: DebugView) -> bool:
        return True


# endregion
