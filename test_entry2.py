from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectEntry, DirectLabel
from panda3d.core import TextNode
import sys

class App(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.setBackgroundColor(0.2, 0.2, 0.2)
        
        y = 0.5
        DirectLabel(text="Without text_pos:", scale=0.05, pos=(-0.5, 0, y), text_fg=(1,1,1,1))
        DirectEntry(
            text="Nickname123",
            scale=0.065,
            pos=(-0.1, 0, y),
            width=13,
            pad=(0.2, 0.2),
            numLines=1,
            frameColor=(0.1, 0.1, 0.1, 1),
            text_fg=(1, 1, 0, 1),
        )

        y = 0.2
        DirectLabel(text="With text_pos=(0.2, 0):", scale=0.05, pos=(-0.5, 0, y), text_fg=(1,1,1,1))
        DirectEntry(
            text="Nickname123",
            scale=0.065,
            pos=(-0.1, 0, y),
            width=13,
            pad=(0.2, 0.2),
            numLines=1,
            text_pos=(0.4, 0),
            frameColor=(0.1, 0.1, 0.1, 1),
            text_fg=(1, 1, 0, 1),
        )
        
        y = -0.1
        DirectLabel(text="With text_pos and frameSize:", scale=0.05, pos=(-0.5, 0, y), text_fg=(1,1,1,1))
        DirectEntry(
            text="Nickname123",
            scale=0.065,
            pos=(-0.1, 0, y),
            width=13,
            numLines=1,
            text_pos=(0.4, 0),
            frameColor=(0.1, 0.1, 0.1, 1),
            text_fg=(1, 1, 0, 1),
        )
        
        self.taskMgr.doMethodLater(1.0, sys.exit, "exit")

app = App()
app.run()
