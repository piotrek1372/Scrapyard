"""
MainMenuScreen — primary hub screen for the Scrapyard game.

Displays player profile summary (nick, balance) and navigation buttons:
  Graj / Wczytaj grę / Profil / Ustawienia / Wyjdź

Transitions are routed through ScrapyardApp._show_screen() and
ScrapyardApp.start_game().
"""
from __future__ import annotations

import logging

from direct.gui.DirectGui import (
    DirectButton,
    DirectFrame,
    DirectLabel,
    OnscreenText,
)
from panda3d.core import TextNode

from src.utils.i18n import t

logger = logging.getLogger("Scrapyard.UI.MainMenu")

# ── Scrapyard industrial palette ──────────────────────────────────────────
_IRON_BG    = (0.06, 0.05, 0.05, 1.0)
_PLATE      = (0.16, 0.14, 0.12, 0.92)
_PLATE_DIM  = (0.12, 0.10, 0.09, 0.85)
_RUST       = (0.72, 0.28, 0.08, 1.0)
_RUST_HOVER = (0.90, 0.38, 0.12, 1.0)
_RUST_DIM   = (0.50, 0.20, 0.06, 1.0)
_PATINA     = (0.22, 0.40, 0.18, 1.0)
_DIRT_TEXT  = (0.82, 0.76, 0.65, 1.0)
_WORN_TEXT  = (0.50, 0.45, 0.38, 1.0)
_AMBER      = (0.95, 0.60, 0.15, 1.0)


class MainMenuScreen:
    """Main menu hub screen.

    Shown after profile creation or on return from the game.
    Displays a styled title, player info, and navigation buttons.
    """

    def __init__(self, app) -> None:
        """Build the main menu screen.

        Args:
            app: ScrapyardApp instance (ShowBase subclass).
        """
        self.app = app
        self._elements: list = []
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        """Constructs all DirectGui elements."""
        # ── Game title ────────────────────────────────────────────────
        title = OnscreenText(
            text=t("game.title").upper(),
            pos=(0, 0.78),
            scale=0.16,
            fg=_RUST,
            shadow=(0.0, 0.0, 0.0, 0.9),
            align=TextNode.ACenter,
            mayChange=False,
        )
        self._elements.append(title)


        # ── Divider line (fake — thin dark panel) ─────────────────────
        divider = DirectFrame(
            frameColor=(_RUST[0], _RUST[1], _RUST[2], 0.45),
            frameSize=(-0.55, 0.55, -0.003, 0.003),
            pos=(0, 0, 0.53),
        )
        self._elements.append(divider)

        # ── Player info card ──────────────────────────────────────────
        profile = getattr(self.app, "_profile", None)
        if profile is not None:
            info_panel = DirectFrame(
                frameColor=_PLATE_DIM,
                frameSize=(-0.55, 0.55, -0.10, 0.10),
                pos=(0, 0, 0.38),
            )
            self._elements.append(info_panel)

            welcome = OnscreenText(
                text=t("menu.welcome", nick=profile.nick),
                pos=(0, 0.04),
                scale=0.058,
                fg=_DIRT_TEXT,
                align=TextNode.ACenter,
                parent=info_panel,
                mayChange=False,
            )
            self._elements.append(welcome)

            balance = OnscreenText(
                text=t("menu.balance", balance=profile.balance),
                pos=(0, -0.04),
                scale=0.048,
                fg=_AMBER,
                align=TextNode.ACenter,
                parent=info_panel,
                mayChange=False,
            )
            self._elements.append(balance)

        # ── Navigation buttons ────────────────────────────────────────
        btn_specs = [
            ("menu.play",      self._on_play,      _RUST,      _DIRT_TEXT),
            ("menu.load_game", self._on_load,       _PLATE,     _DIRT_TEXT),
            ("menu.profile",   self._on_profile,    _PLATE,     _WORN_TEXT),
            ("menu.settings",  self._on_settings,   _PLATE,     _WORN_TEXT),
            ("menu.quit",      self._on_quit,       _PLATE_DIM, _WORN_TEXT),
        ]

        y_start = 0.15
        y_step = -0.18

        for i, (key, cmd, bg, fg) in enumerate(btn_specs):
            y = y_start + i * y_step
            btn = DirectButton(
                text=t(key),
                scale=0.06,
                pos=(0, 0, y),
                command=cmd,
                frameColor=bg,
                frameSize=(-4.5, 4.5, -1.0, 1.3),
                text_fg=fg,
                relief="flat",
                pressEffect=True,
                text_align=TextNode.ACenter,
                pad=(0.4, 0.1),
            )
            # Capture bg/hover for closure
            _bg = bg
            _hover = _RUST_HOVER if bg == _RUST else (
                _PLATE[0] + 0.06,
                _PLATE[1] + 0.05,
                _PLATE[2] + 0.04,
                _PLATE[3],
            )
            btn.bind(
                "enter",
                lambda _, b=btn, h=_hover: b.__setitem__("frameColor", h),
            )
            btn.bind(
                "exit",
                lambda _, b=btn, c=_bg: b.__setitem__("frameColor", c),
            )
            self._elements.append(btn)

        # ── Version / language watermark ──────────────────────────────
        lang = self.app.i18n.get_language().upper()
        watermark = OnscreenText(
            text=t("ui.language", lang=lang),
            pos=(-1.28, -0.92),
            scale=0.042,
            fg=_WORN_TEXT,
            align=TextNode.ALeft,
            mayChange=False,
        )
        self._elements.append(watermark)

    # ── Button actions ────────────────────────────────────────────────────

    def _on_play(self) -> None:
        """Starts a new game session."""
        logger.info("MainMenu → start_game()")
        self.app.start_game()

    def _on_load(self) -> None:
        """Opens the saves screen in load mode."""
        logger.info("MainMenu → saves_load")
        self.app._show_screen("saves_load")

    def _on_profile(self) -> None:
        """Opens the profile screen."""
        logger.info("MainMenu → profile")
        self.app._show_screen("profile")

    def _on_settings(self) -> None:
        """Opens the settings screen (returns to main_menu on save/cancel)."""
        logger.info("MainMenu → settings")
        self.app._show_screen("settings", return_to="main_menu")

    def _on_quit(self) -> None:
        """Exits the application."""
        logger.info("MainMenu → quit")
        self.app.userExit()

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
