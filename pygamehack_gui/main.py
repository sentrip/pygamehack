# import wx


# class TreeView(wx.TreeCtrl): 
#     def __init__(self, parent):
#         super().__init__(parent)

#         self.root = self.AddRoot('Test')

#         self.child = self.AppendItem(self.root, 'Child')


# class App(wx.Frame): 
#    def __init__(self, parent, title):
#         super().__init__(parent, title=title, size=(800,600), style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)
#         self.tree = TreeView(self)


# if __name__ == '__main__':
#    app = wx.App(False)  # Create a new app, don't redirect stdout/stderr to a window.
#    frame = App(None, "TreeView")
#    frame.Show(True)
#    app.MainLoop()


if __name__ == '__main__':
    import pygamehack_gui
    pygamehack_gui.App().run()
