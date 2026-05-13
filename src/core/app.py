"""
ScrapyardApp — Main Panda3D application for Scrapyard.

Handles 3D scene setup, model loading, orbit camera,
placeholder generation, and integration with game logic + i18n.
"""

import math
import sys

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, DirectionalLight, PointLight,
    LVector3, LVector4, WindowProperties,
    CardMaker, TextNode, Filename,
    GeomVertexFormat, GeomVertexData, GeomVertexWriter,
    Geom, GeomTriangles, GeomNode,
    Material, loadPrcFileData
)

# Fix text encoding for special characters (Polish, etc.)
loadPrcFileData("", "text-encoding utf8")

try:
    import simplepbr
    HAS_SIMPLEPBR = True
except ImportError:
    HAS_SIMPLEPBR = False

from src.core.config import Config
from src.core.scrapyard import Scrapyard
from src.utils.i18n import I18n, t, t_item
from src.ui.hud import HUD
from src.core.terrain import TerrainManager
from src.core.environment import EnvironmentManager
from src.core.skybox import SkyboxManager
from src.core.fpv_controller import FPVController
import random
import logging

logger = logging.getLogger("Scrapyard.App")


# ── Category → placeholder color mapping ─────────────────────────────────

CATEGORY_COLORS = {
    "Mechanical": (0.6, 0.6, 0.65, 1.0),   # steel grey
    "Electronics": (0.2, 0.7, 0.3, 1.0),    # circuit green
    "Body":        (0.7, 0.35, 0.2, 1.0),   # rust orange
    "Unique":      (0.8, 0.65, 0.2, 1.0),   # gold
    "Unknown":     (0.5, 0.5, 0.5, 1.0),    # neutral grey
}


class ScrapyardApp(ShowBase):
    """Main Panda3D application for the Scrapyard game.

    Integrates:
    - 3D scene with lighting, ground plane, and orbit camera
    - .glb model loading via panda3d-gltf
    - Placeholder box generation for items without models
    - DirectGui HUD with full i18n support
    - Scrapyard game logic
    """

    def __init__(self, config: Config = None):
        self.game_config = config or Config()
        
        # Apply PRC settings before ShowBase initialization
        res = self.game_config.get("graphics.resolution", [1920, 1080])
        vsync = "t" if self.game_config.get("graphics.vsync") else "f"
        msaa = self.game_config.get("graphics.msaa")
        loadPrcFileData("", "fullscreen true")
        loadPrcFileData("", f"win-size {res[0]} {res[1]}")
        loadPrcFileData("", f"sync-video {vsync}")
        loadPrcFileData("", f"framebuffer-multisample 1")
        loadPrcFileData("", f"multisamples {msaa}")
        
        ShowBase.__init__(self)
        self.setFrameRateMeter(True)

        # ── Window setup ──────────────────────────────────────────────────
        props = WindowProperties()
        props.setTitle("Scrapyard")
        self.win.requestProperties(props)

        # ── i18n ──────────────────────────────────────────────────────────
        self.i18n = I18n()
        logger.info(f"Language: {self.i18n.get_language()}")

        # ── PBR rendering ─────────────────────────────────────────────────
        if HAS_SIMPLEPBR:
            simplepbr.init()

        # ── Background color ──────────────────────────────────────────────
        self.setBackgroundColor(0.08, 0.08, 0.10, 1.0)

        # ── Disable default camera controls ───────────────────────────────
        self.disableMouse()

        # ── Game logic ────────────────────────────────────────────────────
        self.yard = Scrapyard()
        self.current_item = None
        self._displayed_model = None

        # ── Environment & Terrain ─────────────────────────────────────────
        self.env_manager = EnvironmentManager(self)
        self.skybox_manager = SkyboxManager(self)
        self.terrain_manager = TerrainManager(self)
        
        # ── FPV Controller ────────────────────────────────────────────────
        # Bounds = render_dist × chunk_size; FPVController owns cTrav creation.
        _render_dist: int = self.game_config.get("graphics.render_distance", 15)
        _chunk_size: int = 64
        _bounds: float = float(_render_dist * _chunk_size)
        self.fpv_controller = FPVController(
            self, start_pos=LVector3(0, 0, 5), bounds=_bounds
        )

        # ── Update Task ───────────────────────────────────────────────────
        self.taskMgr.add(self._main_update_task, "main_update_task")

        # ── Fonts ─────────────────────────────────────────────────────────
        self._setup_fonts()

        # ── HUD ───────────────────────────────────────────────────────────
        self.hud = HUD(self)

    def _setup_fonts(self):
        """Sets up a unicode font to properly display Polish, etc."""
        from panda3d.core import TextProperties, Filename
        from direct.gui import DirectGuiGlobals as DGG
        
        # Load Arial which supports Polish and many other characters
        font_path = Filename.fromOsSpecific(r"C:\Windows\Fonts\arial.ttf").getFullpath() if sys.platform == "win32" else "Arial.ttf"
        try:
            font = self.loader.loadFont(font_path)
            if font:
                font.setPixelsPerUnit(60)
                TextProperties.setDefaultFont(font)
                DGG.setDefaultFont(font)
        except Exception as e:
            logger.error("Could not load system font for i18n: %s", e)

    def _main_update_task(self, task):
        """Main update loop for managers."""
        player_pos = self.fpv_controller.get_pos()
        # Terrain manager could check if new chunks should be unlocked
        self.terrain_manager.update()
        self.skybox_manager.update(self.camera.getPos(self.render))
        self.env_manager.update(self.camera.getPos(self.render))
        return task.cont

    # ── Public interface (called by HUD) ──────────────────────────────────

    def do_loot(self):
        """Legacy loot action. You might want to update this for FPV."""
        pass

    def show_title(self):
        """Returns to the title/menu screen."""
        self.hud._build_title_screen()

    # ── 3D model display ──────────────────────────────────────────────────

    def _display_item(self, item):
        """Loads and displays the item's 3D model or a placeholder."""
        self._clear_displayed_model()

        if item.has_model():
            self._displayed_model = self._load_glb_model(item.model_path)
        else:
            self._displayed_model = self._create_placeholder(item)

        if self._displayed_model:
            self._displayed_model.reparentTo(self.render)

            # Auto-center and scale
            bounds = self._displayed_model.getTightBounds()
            if bounds:
                bmin, bmax = bounds
                center = (bmin + bmax) / 2.0
                size = (bmax - bmin)
                max_dim = max(size[0], size[1], size[2])
                if max_dim > 0:
                    scale = 2.5 / max_dim
                    self._displayed_model.setScale(scale)
                    self._displayed_model.setPos(-center[0] * scale,
                                                  -center[1] * scale,
                                                  -center[2] * scale + 0.5)

            # Slow spin
            self._displayed_model.hprInterval(12, (360, 0, 0)).loop()

    def _load_glb_model(self, model_path):
        """Loads a .glb model via panda3d-gltf."""
        try:
            panda_path = Filename.fromOsSpecific(model_path)
            model = self.loader.loadModel(panda_path)
            return model
        except Exception as e:
            logger.error("Failed to load model %s: %s", model_path, e)
            return None

    def _create_placeholder(self, item):
        """Creates a procedural colored box as a placeholder for missing models."""
        color = CATEGORY_COLORS.get(item.category, CATEGORY_COLORS["Unknown"])

        # Create a simple box using CardMaker for 6 faces
        root = self.render.attachNewNode("placeholder_root")

        # Use Panda3D built-in box
        box = self.loader.loadModel("models/box")
        if box:
            box.setScale(0.8, 0.8, 0.8)
            box.setColor(*color)
            box.reparentTo(root)
        else:
            # Fallback: create from CardMaker
            box = self._make_box(color)
            box.reparentTo(root)

        root.reparentTo(self.render)
        return root

    def _make_box(self, color):
        """Creates a simple box geometry from CardMaker as fallback."""
        root = self.render.attachNewNode("box_fallback")
        cm = CardMaker("face")
        cm.setFrame(-0.5, 0.5, -0.5, 0.5)
        cm.setColor(*color)

        # 6 faces of a cube
        faces = [
            (0, 0, 0, (0, 0, 0)),        # front
            (180, 0, 0, (0, -1, 0)),      # back
            (90, 0, 0, (0.5, -0.5, 0)),   # right
            (-90, 0, 0, (-0.5, -0.5, 0)), # left
            (0, 90, 0, (0, -0.5, 0.5)),   # top
            (0, -90, 0, (0, -0.5, -0.5)), # bottom
        ]
        for h, p, r, pos in faces:
            face = root.attachNewNode(cm.generate())
            face.setHpr(h, p, r)
            face.setPos(*pos)

        return root

    def _clear_displayed_model(self):
        """Removes the currently displayed 3D model from the scene."""
        if self._displayed_model:
            self._displayed_model.removeNode()
            self._displayed_model = None
