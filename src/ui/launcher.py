"""
Launcher module for configuring game settings before starting the main application.
Uses DirectGUI as a fallback since Tkinter is missing in this environment.
"""
import sys
import logging
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import (
    DirectFrame, DirectLabel, DirectButton, DirectOptionMenu,
    OnscreenText
)
from panda3d.core import WindowProperties, TextNode
from src.core.config import Config

logger = logging.getLogger("Scrapyard.Launcher")

class Launcher(ShowBase):
    """Launcher GUI for Scrapyard using Panda3D's DirectGUI."""
    
    def __init__(self, config: Config):
        # Use a temporary window for the launcher
        ShowBase.__init__(self)
        self.game_config = config
        self.confirmed = False
        
        # Window setup
        props = WindowProperties()
        props.setTitle("Scrapyard - Configuration")
        props.setSize(600, 400)
        self.win.requestProperties(props)
        self.setBackgroundColor(0.1, 0.1, 0.1)
        
        # UI Container
        self.frame = DirectFrame(
            frameColor=(0.2, 0.2, 0.2, 1),
            frameSize=(-0.8, 0.8, -0.6, 0.6),
            pos=(0, 0, 0)
        )
        
        DirectLabel(
            parent=self.frame,
            text="SCRAPYARD CONFIGURATION",
            scale=0.1,
            pos=(0, 0, 0.45),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0)
        )
        
        # Resolution
        DirectLabel(
            parent=self.frame,
            text="Resolution:",
            scale=0.06,
            pos=(-0.4, 0, 0.2),
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0),
            text_align=TextNode.ALeft
        )
        
        res_options = ["1920x1080", "1280x720", "1024x768", "800x600"]
        current_res = f"{config.get('graphics.resolution')[0]}x{config.get('graphics.resolution')[1]}"
        if current_res not in res_options:
            res_options.insert(0, current_res)
            
        self.res_menu = DirectOptionMenu(
            parent=self.frame,
            scale=0.05,
            items=res_options,
            initialitem=res_options.index(current_res),
            pos=(-0.4, 0, 0.1),
            highlightColor=(0.4, 0.4, 0.8, 1)
        )
        
        # Render Distance
        DirectLabel(
            parent=self.frame,
            text="Render Distance (Chunks):",
            scale=0.06,
            pos=(-0.4, 0, -0.1),
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0),
            text_align=TextNode.ALeft
        )
        
        dist_options = ["10", "15", "20", "30", "40"]
        current_dist = str(config.get("graphics.render_distance"))
        
        self.dist_menu = DirectOptionMenu(
            parent=self.frame,
            scale=0.05,
            items=dist_options,
            initialitem=dist_options.index(current_dist) if current_dist in dist_options else 1,
            pos=(-0.4, 0, -0.2),
            highlightColor=(0.4, 0.4, 0.8, 1)
        )
        
        # Start Button
        DirectButton(
            parent=self.frame,
            text="START GAME",
            scale=0.08,
            pos=(0, 0, -0.45),
            command=self.confirm_and_start,
            frameColor=(0.2, 0.5, 0.2, 1),
            text_fg=(1, 1, 1, 1),
            pad=(0.2, 0.1)
        )

    def confirm_and_start(self):
        """Saves settings and closes the launcher window."""
        # Parse resolution
        res_str = self.res_menu.get()
        w, h = map(int, res_str.split('x'))
        self.game_config.set("graphics.resolution", [w, h])
        
        # Parse distance
        dist = int(self.dist_menu.get())
        self.game_config.set("graphics.render_distance", dist)
        
        self.game_config.save()
        self.confirmed = True
        self.taskMgr.stop()
        self.destroy() # Close Panda3D window

def run_launcher(config: Config) -> bool:
    """Entry point to run the launcher. Returns True if game should start."""
    try:
        launcher = Launcher(config)
        launcher.run()
        return launcher.confirmed
    except Exception as e:
        logger.error(f"Launcher failed: {e}")
        return True # Start with defaults if launcher crashes
