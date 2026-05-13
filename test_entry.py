from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectEntry, DirectLabel
from panda3d.core import TextNode
import sys

class App(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.setBackgroundColor(0.2, 0.2, 0.2)
        
        # Original from profile_screen
        y = 0.5
        DirectLabel(
            text="Original:",
            scale=0.052,
            pos=(-0.8, 0, y),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            text_align=TextNode.ALeft,
        )
        DirectEntry(
            text="Nickname123",
            scale=0.065,
            pos=(0.02, 0, y - 0.04),
            width=16,
            numLines=1,
            frameColor=(0.1, 0.1, 0.1, 1),
            text_fg=(1, 1, 0, 1),
        )

        # Proposed fix
        y = 0.2
        DirectLabel(
            text="Fixed 1 (aligned baseline):",
            scale=0.052,
            pos=(-0.8, 0, y),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            text_align=TextNode.ALeft,
        )
        DirectEntry(
            text="Nickname123",
            scale=0.065,
            pos=(-0.2, 0, y),
            width=13,
            numLines=1,
            frameColor=(0.1, 0.1, 0.1, 1),
            text_fg=(1, 1, 0, 1),
        )

        # Proposed fix with padding
        y = -0.1
        DirectLabel(
            text="Fixed 2 (with pad):",
            scale=0.052,
            pos=(-0.8, 0, y),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            text_align=TextNode.ALeft,
        )
        DirectEntry(
            text="Nickname123",
            scale=0.065,
            pos=(-0.2, 0, y),
            width=13,
            numLines=1,
            pad=(0.2, 0.2),
            frameColor=(0.1, 0.1, 0.1, 1),
            text_fg=(1, 1, 0, 1),
        )
        
        self.taskMgr.doMethodLater(1.0, sys.exit, "exit")

app = App()
app.run()
