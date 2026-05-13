"""
ScrapyardApp — Main Panda3D application for Scrapyard.

Single ShowBase instance managing all game states:
  MAIN_MENU → NEW_PROFILE → PLAYING → PAUSED → SETTINGS / PROFILE / SAVES

The 3D world (terrain, environment, FPV) is initialized lazily on
transition to PLAYING and destroyed cleanly on return to MAIN_MENU.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, DirectionalLight,
    LVector3, LVector4, WindowProperties,
    CardMaker, TextNode, Filename,
    GeomVertexFormat, GeomVertexData, GeomVertexWriter,
    Geom, GeomTriangles, GeomNode,
    Material, loadPrcFileData,
)

# Fix text encoding for special characters (Polish, etc.)
loadPrcFileData("", "text-encoding utf8")

try:
    import simplepbr
    HAS_SIMPLEPBR = True
except ImportError:
    HAS_SIMPLEPBR = False

from src.core.config import Config
from src.core.game_state import GameState, StateManager
from src.core.profile_manager import Profile, ProfileManager
from src.core.save_manager import SaveManager
from src.core.scrapyard import Scrapyard
from src.utils.i18n import I18n, t, t_item
from src.utils.path_manager import PathManager
import logging

logger = logging.getLogger("Scrapyard.App")


# ── Category → placeholder color mapping ──────────────────────────────────

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
    - State machine: MAIN_MENU / NEW_PROFILE / PLAYING / PAUSED / …
    - Lazy 3D world initialization (terrain, env, skybox, FPV)
    - ProfileManager and SaveManager
    - DirectGui screens (registered after ShowBase init)
    """

    def __init__(self) -> None:
        """Initialize the application in MAIN_MENU state."""
        self.game_config = Config()

        # Apply window PRC before ShowBase (no fullscreen until Settings)
        res = self.game_config.get("graphics.resolution", [1280, 720])
        vsync = "t" if self.game_config.get("graphics.vsync") else "f"
        msaa = self.game_config.get("graphics.msaa", 4)
        loadPrcFileData("", f"win-size {res[0]} {res[1]}")
        loadPrcFileData("", f"sync-video {vsync}")
        loadPrcFileData("", f"framebuffer-multisample 1")
        loadPrcFileData("", f"multisamples {msaa}")

        ShowBase.__init__(self)

        # ── Window ────────────────────────────────────────────────────
        props = WindowProperties()
        props.setTitle("Scrapyard")
        self.win.requestProperties(props)

        # ── i18n ──────────────────────────────────────────────────────
        self._configure_language()
        self.i18n = I18n()
        logger.info("Language: %s", self.i18n.get_language())

        # ── Fonts ─────────────────────────────────────────────────────
        self._setup_fonts()

        # ── PBR rendering — must be initialized once per process ──────
        # simplepbr.init() creates a FilterManager that cannot be
        # re-created in the same window. Initialize here, not in
        # start_game(), to survive multiple play/cleanup cycles.
        if HAS_SIMPLEPBR:
            simplepbr.init()
            logger.info("simplepbr initialized.")

        # ── Profile & saves ───────────────────────────────────────────
        self._profile: Profile | None = ProfileManager.load()
        path_mgr = PathManager()
        self.save_manager = SaveManager(path_mgr.SAVES_DIR)

        # ── State machine ─────────────────────────────────────────────
        self.state_manager = StateManager()

        # ── 3D world handles (None until start_game()) ─────────────────
        self.env_manager = None
        self.skybox_manager = None
        self.terrain_manager = None
        self.fpv_controller = None
        self._world_active: bool = False

        # ── Screen handles ────────────────────────────────────────────
        self._current_screen = None

        # ── Boot into correct screen ──────────────────────────────────
        # Deferred one frame so the window is fully open before we build GUI
        self.taskMgr.doMethodLater(
            0.05, self._boot_screen, "boot_screen_task"
        )

        logger.info("ScrapyardApp initialized.")

    # ── Language configuration ─────────────────────────────────────────────

    def _configure_language(self) -> None:
        """Applies the language setting from config to i18n singleton."""
        lang_setting = self.game_config.get("language", "auto")
        if lang_setting != "auto":
            I18n().set_language(lang_setting)

    # ── Boot ──────────────────────────────────────────────────────────────

    def _boot_screen(self, task) -> int:
        """Decides the first screen: NewProfile if no profile, else MainMenu.

        Args:
            task: Panda3D task argument (unused).

        Returns:
            task.done to run only once.
        """
        self.disableMouse()
        self.setBackgroundColor(0.06, 0.05, 0.05, 1.0)

        if not ProfileManager.exists() or self._profile is None:
            self._show_screen("new_profile")
        else:
            self._show_screen("main_menu")
        return task.done

    # ── Screen router ──────────────────────────────────────────────────────

    def _show_screen(self, name: str, **kwargs) -> None:
        """Destroys current screen and shows the named one.

        Args:
            name: Screen identifier:
                  'main_menu', 'new_profile', 'settings', 'profile',
                  'saves_load', 'saves_save', 'pause'.
            **kwargs: Extra arguments forwarded to the screen constructor.
        """
        self._destroy_current_screen()

        if name == "main_menu":
            from src.ui.screens.main_menu_screen import MainMenuScreen
            self._current_screen = MainMenuScreen(self)

        elif name == "new_profile":
            from src.ui.screens.new_profile_screen import NewProfileScreen
            self._current_screen = NewProfileScreen(self)

        elif name == "settings":
            from src.ui.screens.settings_screen import SettingsScreen
            self._current_screen = SettingsScreen(
                self, return_to=kwargs.get("return_to", "main_menu")
            )

        elif name == "profile":
            from src.ui.screens.profile_screen import ProfileScreen
            self._current_screen = ProfileScreen(self)

        elif name in ("saves_load", "saves_save"):
            from src.ui.screens.saves_screen import SavesScreen
            mode = "load" if name == "saves_load" else "save"
            self._current_screen = SavesScreen(self, mode=mode)

        elif name == "pause":
            from src.ui.screens.pause_screen import PauseScreen
            self._current_screen = PauseScreen(self)

        else:
            logger.error("Unknown screen: %s", name)

    def _destroy_current_screen(self) -> None:
        """Cleans up the currently active screen if one exists."""
        if self._current_screen is not None:
            try:
                self._current_screen.destroy()
            except Exception as exc:
                logger.warning("Screen destroy error: %s", exc)
            self._current_screen = None

    # ── 3D World lifecycle ────────────────────────────────────────────────

    def start_game(self, load_save_id: str | None = None) -> None:
        """Initializes the 3D world and transitions to PLAYING state.

        Called from MainMenuScreen ("Play") or SavesScreen ("Load").
        Safe to call multiple times only after cleanup_world() has run.

        Args:
            load_save_id: If not None, restore player position from this
                          save UUID after world initialization.
        """
        if self._world_active:
            logger.warning("start_game() called while world already active.")
            return

        logger.info("Initializing 3D world…")

        self.setBackgroundColor(0.08, 0.08, 0.10, 1.0)
        self.setFrameRateMeter(True)

        # ── Managers ──────────────────────────────────────────────────
        from src.core.environment import EnvironmentManager
        from src.core.skybox import SkyboxManager
        from src.core.terrain import TerrainManager
        from src.core.fpv_controller import FPVController

        self.env_manager = EnvironmentManager(self)
        self.skybox_manager = SkyboxManager(self)
        self.terrain_manager = TerrainManager(self)

        _render_dist: int = self.game_config.get(
            "graphics.render_distance", 15
        )
        _chunk_size: int = 64
        _bounds: float = float(_render_dist * _chunk_size)
        self.fpv_controller = FPVController(
            self, start_pos=LVector3(0, 0, 5), bounds=_bounds
        )

        # ── Main update task ──────────────────────────────────────────
        self.taskMgr.add(
            self._main_update_task, "main_update_task", sort=20
        )

        self._world_active = True

        # ── Restore save if requested ─────────────────────────────────
        if load_save_id is not None:
            self.save_manager.load_game(load_save_id, self)

        # ── Dismiss menu screen ───────────────────────────────────────
        self._destroy_current_screen()

        self.state_manager.transition(GameState.PLAYING)
        logger.info("3D world ready.")

    def cleanup_world(self) -> None:
        """Destroys the 3D world and returns to a clean 2D state.

        Safe to call even if world is not active (no-op in that case).
        """
        if not self._world_active:
            return

        logger.info("Cleaning up 3D world…")

        # Stop update task
        self.taskMgr.remove("main_update_task")

        # Destroy FPV
        if self.fpv_controller is not None:
            try:
                self.fpv_controller.destroy()
            except AttributeError:
                # FPVController has no explicit destroy; remove its task
                self.taskMgr.remove("fpv_update_task")
                if hasattr(self.fpv_controller, "player_np"):
                    self.fpv_controller.player_np.removeNode()
            self.fpv_controller = None

        # Destroy world managers
        for attr in ("terrain_manager", "env_manager", "skybox_manager"):
            mgr = getattr(self, attr, None)
            if mgr is not None:
                try:
                    mgr.cleanup()
                except AttributeError:
                    pass
                setattr(self, attr, None)

        # Restore background
        self.setBackgroundColor(0.06, 0.05, 0.05, 1.0)
        self.setFrameRateMeter(False)

        self._world_active = False
        logger.info("3D world cleaned up.")

    # ── Pause / resume ────────────────────────────────────────────────────

    def pause(self) -> None:
        """Pauses the game: releases FPV mouse, shows pause overlay.

        Only has effect when in PLAYING state.
        """
        if not self.state_manager.is_in(GameState.PLAYING):
            return

        if self.fpv_controller is not None:
            self.fpv_controller.set_input_mode(locked=False)

        self.state_manager.transition(GameState.PAUSED)
        self._show_screen("pause")
        logger.debug("Game paused.")

    def resume(self) -> None:
        """Resumes the game from pause: hides overlay, re-locks FPV mouse.

        Only has effect when in PAUSED state.
        """
        if not self.state_manager.is_in(GameState.PAUSED):
            return

        self._destroy_current_screen()

        if self.fpv_controller is not None:
            self.fpv_controller.set_input_mode(locked=True)

        self.state_manager.transition(GameState.PLAYING)
        logger.debug("Game resumed.")

    def return_to_main_menu(self) -> None:
        """Destroys the 3D world and navigates to the main menu.

        Can be called from the pause screen or any other context.
        """
        self.cleanup_world()
        self.state_manager.transition(GameState.MAIN_MENU)
        self._show_screen("main_menu")

    # ── Font setup ────────────────────────────────────────────────────────

    def _setup_fonts(self) -> None:
        """Loads system fonts for all supported scripts.

        Populates ``self.script_fonts`` with DynamicTextFont objects keyed by
        script name.  Latin/Cyrillic is set as the global DirectGui default.
        Script-specific fonts (CJK, Arabic, Indic) are used per-widget in the
        language selection screen so each language name renders in its own
        native typeface.

        Font selection (Windows built-ins, no external download needed):
            latin      → Arial              (Latin, Cyrillic, Greek)
            cjk_zh     → SimSun             (Simplified Chinese)
            cjk_ja     → Meiryo             (Japanese, also covers CJK)
            cjk_ko     → Malgun Gothic      (Korean)
            arabic     → Tahoma             (Arabic, Hebrew)
            devanagari → Mangal             (Hindi / Devanagari)
            bengali    → Vrinda             (Bengali)
        """
        from panda3d.core import TextProperties
        from direct.gui import DirectGuiGlobals as DGG

        # Script key → Windows font path
        _WIN_FONTS: dict[str, str] = {
            "latin":      r"C:\Windows\Fonts\arial.ttf",
            "cjk_zh":     r"C:\Windows\Fonts\simsun.ttc",
            # Yu Gothic R — Japanese CJK (Meiryo absent on this machine)
            "cjk_ja":     r"C:\Windows\Fonts\YuGothR.ttc",
            "cjk_ko":     r"C:\Windows\Fonts\malgun.ttf",
            "arabic":     r"C:\Windows\Fonts\tahoma.ttf",
            # Nirmala UI — covers Devanagari (Hindi) + Bengali
            "devanagari": r"C:\Windows\Fonts\Nirmala.ttc",
            "bengali":    r"C:\Windows\Fonts\Nirmala.ttc",
        }

        self.script_fonts: dict[str, object] = {}

        for script, path in _WIN_FONTS.items():
            try:
                font = self.loader.loadFont(
                    Filename.fromOsSpecific(path).getFullpath()
                )
                if font:
                    font.setPixelsPerUnit(60)
                    self.script_fonts[script] = font
                    logger.info("Font loaded: %s → %s", script, path)
            except Exception as exc:
                logger.warning("Font unavailable (%s): %s", script, exc)

        # Latin/Cyrillic as global default for all DirectGui widgets
        latin_font = self.script_fonts.get("latin")
        if latin_font:
            TextProperties.setDefaultFont(latin_font)
            DGG.setDefaultFont(latin_font)


    # ── Main update task ──────────────────────────────────────────────────

    def _main_update_task(self, task) -> int:
        """Per-frame update for terrain, environment, and sky.

        Returns:
            task.cont to keep the task alive.
        """
        if self.terrain_manager is not None:
            self.terrain_manager.update()
        if self.env_manager is not None:
            self.env_manager.update(self.camera.getPos(self.render))
        return task.cont

    # ── Legacy public API (called by HUD) ─────────────────────────────────

    def do_loot(self) -> None:
        """Legacy loot action — placeholder for FPV gameplay."""
        pass

    def show_title(self) -> None:
        """Returns to the title/menu screen (legacy HUD callback)."""
        pass

    # ── 3D model display (legacy — used by HUD item inspect) ──────────────

    def _display_item(self, item) -> None:
        """Loads and displays the item's 3D model or a placeholder."""
        self._clear_displayed_model()
        if not hasattr(self, "_displayed_model"):
            self._displayed_model = None

        if item.has_model():
            self._displayed_model = self._load_glb_model(item.model_path)
        else:
            self._displayed_model = self._create_placeholder(item)

        if self._displayed_model:
            self._displayed_model.reparentTo(self.render)
            bounds = self._displayed_model.getTightBounds()
            if bounds:
                bmin, bmax = bounds
                center = (bmin + bmax) / 2.0
                size = bmax - bmin
                max_dim = max(size[0], size[1], size[2])
                if max_dim > 0:
                    scale = 2.5 / max_dim
                    self._displayed_model.setScale(scale)
                    self._displayed_model.setPos(
                        -center[0] * scale,
                        -center[1] * scale,
                        -center[2] * scale + 0.5,
                    )
            self._displayed_model.hprInterval(12, (360, 0, 0)).loop()

    def _load_glb_model(self, model_path: str):
        """Loads a .glb model via panda3d-gltf.

        Args:
            model_path: OS-specific path string to the .glb file.

        Returns:
            Loaded NodePath, or None on failure.
        """
        try:
            panda_path = Filename.fromOsSpecific(model_path)
            return self.loader.loadModel(panda_path)
        except Exception as exc:
            logger.error("Failed to load model %s: %s", model_path, exc)
            return None

    def _create_placeholder(self, item):
        """Creates a procedural colored box for items without models.

        Args:
            item: Item instance from Scrapyard.loot().

        Returns:
            NodePath of the placeholder root node.
        """
        color = CATEGORY_COLORS.get(item.category, CATEGORY_COLORS["Unknown"])
        root = self.render.attachNewNode("placeholder_root")
        box = self.loader.loadModel("models/box")
        if box:
            box.setScale(0.8, 0.8, 0.8)
            box.setColor(*color)
            box.reparentTo(root)
        else:
            self._make_box(color).reparentTo(root)
        root.reparentTo(self.render)
        return root

    def _make_box(self, color: tuple):
        """Creates a simple box geometry from CardMaker as fallback.

        Args:
            color: RGBA tuple for the box faces.

        Returns:
            NodePath of the box root.
        """
        root = self.render.attachNewNode("box_fallback")
        cm = CardMaker("face")
        cm.setFrame(-0.5, 0.5, -0.5, 0.5)
        cm.setColor(*color)
        faces = [
            (0,    0,   0,  (0, 0, 0)),
            (180,  0,   0,  (0, -1, 0)),
            (90,   0,   0,  (0.5, -0.5, 0)),
            (-90,  0,   0,  (-0.5, -0.5, 0)),
            (0,    90,  0,  (0, -0.5, 0.5)),
            (0,   -90,  0,  (0, -0.5, -0.5)),
        ]
        for h, p, r, pos in faces:
            face = root.attachNewNode(cm.generate())
            face.setHpr(h, p, r)
            face.setPos(*pos)
        return root

    def _clear_displayed_model(self) -> None:
        """Removes the currently displayed 3D model from the scene."""
        displayed = getattr(self, "_displayed_model", None)
        if displayed:
            displayed.removeNode()
            self._displayed_model = None
