import logging
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

log = logging.getLogger('pygamehack')


class TextHandler(logging.Handler):
    # This class allows you to log to a Tkinter Text or ScrolledText widget
    # Adapted from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06

    def __init__(self, text):
        super().__init__()
        self.text = text

    def emit(self, record):
        msg = self.format(record)

        def append():
            self.text.configure(state='normal')
            self.text.insert(tk.END, msg + '\n')
            self.text.configure(state='disabled')
            # Autoscroll to the bottom
            self.text.yview(tk.END)

        # This is necessary because we can't modify the Text from other threads
        self.text.after(0, append)


class LogView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)

        label = tk.Label(self, text='Log')

        self.text = ScrolledText(self)

        label.pack(side=tk.TOP, fill=tk.X, expand=True)
        self.text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        log.addHandler(TextHandler(self.text))


class LogWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)

        self.wm_title('PyCheatEngine - Log')

        log_view = LogView(self)

        log_view.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.protocol('WM_DELETE_WINDOW', self.iconify)
