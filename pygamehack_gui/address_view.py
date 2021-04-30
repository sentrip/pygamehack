import tkinter as tk


class AddressView(tk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.scrollbar = tk.Scrollbar(self)
        self.title_frame = tk.Frame(self)
        self.title = tk.Label(self.title_frame, text='Addresses')
        self.listbox = tk.Listbox(self, yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.listbox.yview)
        
        self.title.pack(side=tk.LEFT, fill=tk.X, padx=16)
        self.title_frame.pack(side=tk.TOP, fill=tk.X)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
