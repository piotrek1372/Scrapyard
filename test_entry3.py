from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectEntry, DirectLabel
import sys

class App(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.setBackgroundColor(0.2, 0.2, 0.2)
        
        y = 0.5
        DirectEntry(
            text="STATIC TEXT",
            initialText="EDITABLE",
            scale=0.065,
            pos=(-0.1, 0, y),
            width=13,
            pad=(0.2, 0.2),
            numLines=1,
            frameColor=(0.1, 0.1, 0.1, 1),
            text_fg=(1, 1, 0, 1),
        )
        
        self.taskMgr.doMethodLater(1.0, sys.exit, "exit")

app = App()
app.run()
