"""
PauseScreen — in-game overlay shown when the player presses ESC.

Semi-transparent dark panel over the 3D world with buttons:
  Wznów / Zapisz grę / Ustawienia / Wróć do menu

Does NOT destroy the 3D world — that only happens on 'Wróć do menu'.
"""
from __future__ import annotations

import logging

from direct.gui.DirectGui import (
    DirectButton,
    DirectFrame,
    OnscreenText,
)
from panda3d.core import TextNode

from src.utils.i18n import t

logger = logging.getLogger("Scrapyard.UI.Pause")

# ── Palette ───────────────────────────────────────────────────────────────
_OVERLAY    = (0.03, 0.02, 0.02, 0.72)   # dark semi-transparent overlay
_PLATE      = (0.15, 0.13, 0.11, 0.96)
_PLATE_DIM  = (0.10, 0.09, 0.08, 0.92)
_RUST       = (0.72, 0.28, 0.08, 1.0)
_RUST_HOVER = (0.90, 0.38, 0.12, 1.0)
_RED_EXIT   = (0.55, 0.12, 0.06, 1.0)
_RED_HOVER  = (0.75, 0.18, 0.08, 1.0)
_DIRT_TEXT  = (0.82, 0.76, 0.65, 1.0)
_WORN_TEXT  = (0.50, 0.45, 0.38, 1.0)


class PauseScreen:
    """In-game pause overlay.

    Rendered on top of the frozen 3D scene. The world is NOT destroyed
    until the player explicitly chooses 'Main Menu'.
    """

    def __init__(self, app) -> None:
        """Build the pause overlay.

        Args:
            app: ScrapyardApp instance.
        """
        self.app = app
        self._elements: list = []
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        """Constructs the pause overlay elements."""
        # Full-screen dark backdrop (not completely opaque — world visible)
        backdrop = DirectFrame(
            frameColor=_OVERLAY,
            frameSize=(-2.0, 2.0, -2.0, 2.0),
            pos=(0, 0, 0),
            sortOrder=100,
        )
        self._elements.append(backdrop)

        # Central panel
        panel = DirectFrame(
            parent=backdrop,
            frameColor=_PLATE,
            frameSize=(-0.58, 0.58, -0.62, 0.52),
            pos=(0, 0, 0),
        )
        self._elements.append(panel)

        # Title
        title = OnscreenText(
            text=t("pause.title"),
            pos=(0, 0.40),
            scale=0.13,
            fg=_RUST,
            shadow=(0, 0, 0, 0.9),
            align=TextNode.ACenter,
            parent=panel,
            mayChange=False,
        )
        self._elements.append(title)

        # Thin rust divider
        divider = DirectFrame(
            parent=panel,
            frameColor=(_RUST[0], _RUST[1], _RUST[2], 0.5),
            frameSize=(-0.40, 0.40, -0.003, 0.003),
            pos=(0, 0, 0.28),
        )
        self._elements.append(divider)

        # ── Buttons ───────────────────────────────────────────────────
        btn_specs = [
            ("pause.resume",    self._on_resume,      _RUST,    _DIRT_TEXT, 0.080),
            ("pause.save_game", self._on_save_game,   _PLATE,   _DIRT_TEXT, 0.068),
            ("pause.settings",  self._on_settings,    _PLATE,   _WORN_TEXT, 0.065),
            ("pause.main_menu", self._on_main_menu,   _RED_EXIT,_DIRT_TEXT, 0.065),
        ]

        y_start = 0.14
        y_step = -0.19

        for i, (key, cmd, bg, fg, scale) in enumerate(btn_specs):
            y = y_start + i * y_step
            btn = DirectButton(
                parent=panel,
                text=t(key),
                scale=scale,
                pos=(0, 0, y),
                command=cmd,
                frameColor=bg,
                text_fg=fg,
                relief="flat",
                pressEffect=True,
                text_align=TextNode.ACenter,
                pad=(0.35, 0.18),
            )
            _bg = bg
            _hover = (
                _RUST_HOVER if bg == _RUST
                else _RED_HOVER if bg == _RED_EXIT
                else (bg[0] + 0.06, bg[1] + 0.05, bg[2] + 0.04, bg[3])
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

    # ── Actions ───────────────────────────────────────────────────────────

    def _on_resume(self) -> None:
        """Resumes gameplay (destroys this overlay, re-locks mouse)."""
        logger.info("Pause → resume")
        self.app.resume()

    def _on_save_game(self) -> None:
        """Opens the saves screen in save mode."""
        logger.info("Pause → saves_save")
        self.app._show_screen("saves_save")

    def _on_settings(self) -> None:
        """Opens settings, which will return to pause on close."""
        logger.info("Pause → settings (return_to=pause)")
        self.app._show_screen("settings", return_to="pause")

    def _on_main_menu(self) -> None:
        """Destroys the 3D world and navigates to the main menu."""
        logger.info("Pause → main_menu (cleanup_world)")
        self.app.return_to_main_menu()

    # ── Cleanup ───────────────────────────────────────────────────────────

    def destroy(self) -> None:
        """Removes all pause overlay elements."""
        for elem in self._elements:
            try:
                elem.destroy()
            except Exception:
                try:
                    elem.removeNode()
                except Exception:
                    pass
        self._elements.clear()
