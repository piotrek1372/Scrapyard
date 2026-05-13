from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectEntry, DirectLabel
import sys

class App(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.setBackgroundColor(0.2, 0.2, 0.2)
        
        self.entry = DirectEntry(text="Hidden entry", scale=0.1, pos=(0,0,0))
        self.entry.hide()
        
        self.taskMgr.doMethodLater(1.0, sys.exit, "exit")

app = App()
app.run()
