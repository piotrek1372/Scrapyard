"""
SettingsScreen — multi-tab settings panel for Scrapyard.

Tabs: Graphics | Audio | Performance | Language
Changes are applied to Config on Save; Cancel discards them.
Returns to the screen specified by return_to (default: 'main_menu').
"""
from __future__ import annotations

import logging
from typing import Any

from direct.gui.DirectGui import (
    DirectButton,
    DirectCheckButton,
    DirectFrame,
    DirectLabel,
    DirectOptionMenu,
    DirectSlider,
    OnscreenText,
)
from panda3d.core import TextNode

from src.utils.i18n import t
from src.utils.i18n import SUPPORTED_LANGUAGES


logger = logging.getLogger("Scrapyard.UI.Settings")

# ── Palette ───────────────────────────────────────────────────────────────
_IRON_BG    = (0.06, 0.05, 0.05, 1.0)
_PLATE      = (0.16, 0.14, 0.12, 0.95)
_PLATE_DIM  = (0.12, 0.10, 0.09, 0.90)
_RUST       = (0.72, 0.28, 0.08, 1.0)
_RUST_HOVER = (0.90, 0.38, 0.12, 1.0)
_DIRT_TEXT  = (0.82, 0.76, 0.65, 1.0)
_WORN_TEXT  = (0.50, 0.45, 0.38, 1.0)
_AMBER      = (0.95, 0.60, 0.15, 1.0)
_GREEN_OK   = (0.30, 0.70, 0.25, 1.0)


class SettingsScreen:
    """Settings panel with four tabs (graphics, audio, performance, language).

    All changes are buffered in _pending until Save is pressed.
    Cancel returns to the originating screen without writing to disk.
    """

    _TABS = ["tab_graphics", "tab_audio", "tab_performance", "tab_language"]

    def __init__(self, app, return_to: str = "main_menu") -> None:
        """Build the settings screen.

        Args:
            app: ScrapyardApp instance.
            return_to: Screen name to navigate to on Save or Cancel.
        """
        self.app = app
        self._return_to = return_to
        self._elements: list = []
        self._tab_buttons: dict = {}
        self._tab_panels: dict = {}
        self._pending: dict = {}     # key_path → new value
        self._active_tab = "tab_graphics"
        self._status_label = None
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        """Constructs the full settings layout."""
        # Title
        title = OnscreenText(
            text=t("settings.title"),
            pos=(0, 0.87),
            scale=0.09,
            fg=_RUST,
            shadow=(0, 0, 0, 0.8),
            align=TextNode.ACenter,
            mayChange=False,
        )
        self._elements.append(title)

        # Outer container
        container = DirectFrame(
            frameColor=_PLATE,
            frameSize=(-0.90, 0.90, -0.72, 0.72),
            pos=(0, 0, 0.06),
        )
        self._elements.append(container)

        # ── Tab bar ───────────────────────────────────────────────────
        tab_x_start = -0.78
        tab_w = 0.42
        for i, tab_key in enumerate(self._TABS):
            x = tab_x_start + i * tab_w
            btn = DirectButton(
                parent=container,
                text=t(f"settings.{tab_key}"),
                scale=0.058,
                pos=(x + tab_w / 2, 0, 0.60),
                command=self._on_tab,
                extraArgs=[tab_key],
                frameColor=_PLATE_DIM,
                text_fg=_WORN_TEXT,
                relief="flat",
                text_align=TextNode.ACenter,
            )
            self._tab_buttons[tab_key] = btn
            self._elements.append(btn)

        # ── Content panels (one per tab) ──────────────────────────────
        for tab_key in self._TABS:
            panel = DirectFrame(
                parent=container,
                frameColor=(0, 0, 0, 0),
                frameSize=(-0.85, 0.85, -0.58, 0.50),
                pos=(0, 0, 0.0),
            )
            self._tab_panels[tab_key] = panel
            self._elements.append(panel)
            panel.hide()

        self._populate_graphics(self._tab_panels["tab_graphics"])
        self._populate_audio(self._tab_panels["tab_audio"])
        self._populate_performance(self._tab_panels["tab_performance"])
        self._populate_language(self._tab_panels["tab_language"])

        # ── Status label ──────────────────────────────────────────────
        self._status_label = OnscreenText(
            text="",
            pos=(0, -0.73),
            scale=0.052,
            fg=_GREEN_OK,
            align=TextNode.ACenter,
            mayChange=True,
        )
        self._elements.append(self._status_label)

        # ── Save / Cancel buttons ─────────────────────────────────────
        save_btn = DirectButton(
            text=t("settings.save"),
            scale=0.068,
            pos=(-0.22, 0, -0.84),
            command=self._on_save,
            frameColor=_RUST,
            text_fg=_DIRT_TEXT,
            relief="flat",
            pressEffect=True,
            text_align=TextNode.ACenter,
        )
        self._elements.append(save_btn)

        cancel_btn = DirectButton(
            text=t("settings.cancel"),
            scale=0.068,
            pos=(0.22, 0, -0.84),
            command=self._on_cancel,
            frameColor=_PLATE_DIM,
            text_fg=_WORN_TEXT,
            relief="flat",
            pressEffect=True,
            text_align=TextNode.ACenter,
        )
        self._elements.append(cancel_btn)

        # Activate first tab
        self._on_tab("tab_graphics")

    # ── Tab population helpers ────────────────────────────────────────────

    def _row(
        self,
        parent,
        label_key: str,
        y: float,
        widget,
    ) -> None:
        """Places a label + widget pair at the given y offset.

        Args:
            parent: Parent DirectGui node.
            label_key: i18n key for the row label.
            y: Vertical offset within the panel.
            widget: Already-constructed widget node.
        """
        lbl = DirectLabel(
            parent=parent,
            text=t(f"settings.{label_key}"),
            scale=0.058,
            pos=(-0.60, 0, y),
            text_fg=_DIRT_TEXT,
            frameColor=(0, 0, 0, 0),
            text_align=TextNode.ALeft,
        )
        self._elements.append(lbl)

    def _populate_graphics(self, panel) -> None:
        """Builds the graphics tab content."""
        cfg = self.app.game_config
        y = 0.38

        # Resolution
        res_options = ["1920x1080", "1280x720", "1024x768", "800x600"]
        curr_res = cfg.get("graphics.resolution", [1280, 720])
        curr_str = f"{curr_res[0]}x{curr_res[1]}"
        if curr_str not in res_options:
            res_options.insert(0, curr_str)
        menu = DirectOptionMenu(
            parent=panel,
            scale=0.055,
            items=res_options,
            initialitem=res_options.index(curr_str),
            pos=(0.15, 0, y),
            frameColor=_PLATE_DIM,
            text_fg=_DIRT_TEXT,
            highlightColor=_RUST,
            command=lambda v: self._pending.__setitem__(
                "graphics.resolution",
                [int(x) for x in v.split("x")],
            ),
        )
        self._elements.append(menu)
        self._row(panel, "resolution", y, menu)

        # VSync
        y -= 0.14
        vsync_val = [1 if cfg.get("graphics.vsync") else 0]
        cb = DirectCheckButton(
            parent=panel,
            text="",
            scale=0.06,
            pos=(0.15, 0, y),
            isChecked=cfg.get("graphics.vsync", True),
            frameColor=_PLATE_DIM,
            text_fg=_DIRT_TEXT,
            command=lambda v: self._pending.__setitem__("graphics.vsync", bool(v)),
        )
        self._elements.append(cb)
        self._row(panel, "vsync", y, cb)

        # Render distance
        y -= 0.14
        dist_options = ["10", "15", "20", "30", "40"]
        curr_dist = str(cfg.get("graphics.render_distance", 15))
        menu2 = DirectOptionMenu(
            parent=panel,
            scale=0.055,
            items=dist_options,
            initialitem=(
                dist_options.index(curr_dist)
                if curr_dist in dist_options
                else 1
            ),
            pos=(0.15, 0, y),
            frameColor=_PLATE_DIM,
            text_fg=_DIRT_TEXT,
            highlightColor=_RUST,
            command=lambda v: self._pending.__setitem__(
                "graphics.render_distance", int(v)
            ),
        )
        self._elements.append(menu2)
        self._row(panel, "render_distance", y, menu2)

        # MSAA
        y -= 0.14
        msaa_options = ["0", "2", "4", "8"]
        curr_msaa = str(cfg.get("graphics.msaa", 4))
        menu3 = DirectOptionMenu(
            parent=panel,
            scale=0.055,
            items=msaa_options,
            initialitem=(
                msaa_options.index(curr_msaa)
                if curr_msaa in msaa_options
                else 2
            ),
            pos=(0.15, 0, y),
            frameColor=_PLATE_DIM,
            text_fg=_DIRT_TEXT,
            highlightColor=_RUST,
            command=lambda v: self._pending.__setitem__(
                "graphics.msaa", int(v)
            ),
        )
        self._elements.append(menu3)
        self._row(panel, "msaa", y, menu3)

    def _populate_audio(self, panel) -> None:
        """Builds the audio tab content."""
        cfg = self.app.game_config
        y = 0.38

        def _slider(key: str, initial: float, y_pos: float) -> None:
            sl = DirectSlider(
                parent=panel,
                range=(0.0, 1.0),
                value=initial,
                pageSize=0.05,
                scale=0.45,
                pos=(0.30, 0, y_pos),
                frameColor=_PLATE_DIM,
                thumb_frameColor=_RUST,
                command=lambda: self._pending.__setitem__(key, sl["value"]),
            )
            self._elements.append(sl)

        _slider("audio.master_volume", cfg.get("audio.master_volume", 1.0), y)
        self._row(panel, "master_volume", y, None)

        y -= 0.18
        _slider("audio.music_volume", cfg.get("audio.music_volume", 0.7), y)
        self._row(panel, "music_volume", y, None)

        y -= 0.18
        _slider("audio.sfx_volume", cfg.get("audio.sfx_volume", 1.0), y)
        self._row(panel, "sfx_volume", y, None)

        y -= 0.18
        cb = DirectCheckButton(
            parent=panel,
            text="",
            scale=0.06,
            pos=(0.15, 0, y),
            isChecked=cfg.get("audio.muted", False),
            frameColor=_PLATE_DIM,
            command=lambda v: self._pending.__setitem__("audio.muted", bool(v)),
        )
        self._elements.append(cb)
        self._row(panel, "muted", y, cb)

    def _populate_performance(self, panel) -> None:
        """Builds the performance tab content."""
        cfg = self.app.game_config
        y = 0.38

        shadow_opts = ["off", "low", "medium", "high"]
        curr_shadow = cfg.get("performance.shadow_quality", "medium")
        menu = DirectOptionMenu(
            parent=panel,
            scale=0.055,
            items=shadow_opts,
            initialitem=(
                shadow_opts.index(curr_shadow)
                if curr_shadow in shadow_opts
                else 2
            ),
            pos=(0.15, 0, y),
            frameColor=_PLATE_DIM,
            text_fg=_DIRT_TEXT,
            highlightColor=_RUST,
            command=lambda v: self._pending.__setitem__(
                "performance.shadow_quality", v
            ),
        )
        self._elements.append(menu)
        self._row(panel, "shadow_quality", y, menu)

        y -= 0.14
        texture_opts = ["low", "medium", "high"]
        curr_tex = cfg.get("performance.texture_quality", "high")
        menu2 = DirectOptionMenu(
            parent=panel,
            scale=0.055,
            items=texture_opts,
            initialitem=(
                texture_opts.index(curr_tex)
                if curr_tex in texture_opts
                else 2
            ),
            pos=(0.15, 0, y),
            frameColor=_PLATE_DIM,
            text_fg=_DIRT_TEXT,
            highlightColor=_RUST,
            command=lambda v: self._pending.__setitem__(
                "performance.texture_quality", v
            ),
        )
        self._elements.append(menu2)
        self._row(panel, "texture_quality", y, menu2)

        y -= 0.14
        fps_options = [t("settings.fps_unlimited"), "30", "60", "120", "144"]
        curr_fps = cfg.get("performance.fps_limit", 0)
        curr_fps_str = (
            t("settings.fps_unlimited") if curr_fps == 0 else str(curr_fps)
        )
        menu3 = DirectOptionMenu(
            parent=panel,
            scale=0.055,
            items=fps_options,
            initialitem=(
                fps_options.index(curr_fps_str)
                if curr_fps_str in fps_options
                else 0
            ),
            pos=(0.15, 0, y),
            frameColor=_PLATE_DIM,
            text_fg=_DIRT_TEXT,
            highlightColor=_RUST,
            command=lambda v: self._pending.__setitem__(
                "performance.fps_limit",
                0 if v == t("settings.fps_unlimited") else int(v),
            ),
        )
        self._elements.append(menu3)
        self._row(panel, "fps_limit", y, menu3)

    def _populate_language(self, panel) -> None:
        """Builds the language selection tab content."""
        # Human-readable display names for each language code
        _LANG_NAMES = {
            "en": "English",  "zh": "中文",   "hi": "हिन्दी",
            "es": "Español",  "ar": "العربية", "bn": "বাংলা",
            "pt": "Português","ja": "日本語",  "ko": "한국어",
            "de": "Deutsch",  "fr": "Français","it": "Italiano",
            "tr": "Türkçe",   "ru": "Русский", "pl": "Polski",
        }
        curr_lang = self.app.i18n.get_language()
        lang_items = [
            f"{code} — {_LANG_NAMES.get(code, code)}"
            for code in SUPPORTED_LANGUAGES
        ]
        curr_item = f"{curr_lang} — {_LANG_NAMES.get(curr_lang, curr_lang)}"
        if curr_item not in lang_items:
            curr_item = lang_items[0]

        y = 0.20
        lbl = DirectLabel(
            parent=panel,
            text=t("settings.tab_language"),
            scale=0.065,
            pos=(-0.60, 0, y + 0.14),
            text_fg=_DIRT_TEXT,
            frameColor=(0, 0, 0, 0),
            text_align=TextNode.ALeft,
        )
        self._elements.append(lbl)

        menu = DirectOptionMenu(
            parent=panel,
            scale=0.058,
            items=lang_items,
            initialitem=lang_items.index(curr_item),
            pos=(0, 0, y),
            frameColor=_PLATE_DIM,
            text_fg=_DIRT_TEXT,
            highlightColor=_RUST,
            command=lambda v: self._pending.__setitem__(
                "language", v.split(" — ")[0]
            ),
        )
        self._elements.append(menu)

    # ── Tab switching ─────────────────────────────────────────────────────

    def _on_tab(self, tab_key: str) -> None:
        """Activates the selected tab panel.

        Args:
            tab_key: Key from _TABS (e.g. 'tab_graphics').
        """
        self._active_tab = tab_key
        for key, panel in self._tab_panels.items():
            if key == tab_key:
                panel.show()
            else:
                panel.hide()
        for key, btn in self._tab_buttons.items():
            btn["frameColor"] = _RUST if key == tab_key else _PLATE_DIM
            btn["text_fg"] = _DIRT_TEXT if key == tab_key else _WORN_TEXT

    # ── Save / Cancel ─────────────────────────────────────────────────────

    def _on_save(self) -> None:
        """Applies all pending changes to Config and writes to disk."""
        cfg = self.app.game_config
        for key_path, value in self._pending.items():
            cfg.set(key_path, value)

        # Apply language change immediately
        if "language" in self._pending:
            lang = self._pending["language"]
            self.app.i18n.set_language(lang)

        cfg.save()
        self._pending.clear()

        if self._status_label is not None:
            self._status_label.setText(t("settings.saved"))

        logger.info("Settings saved. Returning to %s", self._return_to)
        self.app._show_screen(self._return_to)

    def _on_cancel(self) -> None:
        """Discards pending changes and returns to the originating screen."""
        self._pending.clear()
        logger.info("Settings cancelled. Returning to %s", self._return_to)
        self.app._show_screen(self._return_to)

    # ── Cleanup ───────────────────────────────────────────────────────────

    def destroy(self) -> None:
        """Removes all GUI elements from the scene."""
        for elem in self._elements:
            try:
                elem.destroy()
            except Exception:
                try:
                    elem.removeNode()
                except Exception:
                    pass
        self._elements.clear()
