"""
NewProfileScreen — first-run screen asking the player for a nickname.

Shown once, when no ~/.scrapyard/profile.json is found.
On successful submission, creates the profile and transitions to MainMenu.
"""
from __future__ import annotations

import logging

from direct.gui.DirectGui import (
    DirectButton,
    DirectEntry,
    DirectFrame,
    DirectLabel,
    OnscreenText,
)
from panda3d.core import TextNode

from src.core.profile_manager import ProfileManager
from src.utils.i18n import t

logger = logging.getLogger("Scrapyard.UI.NewProfile")

# ── Scrapyard industrial palette ──────────────────────────────────────────
_IRON_BG    = (0.06, 0.05, 0.05, 1.0)
_PLATE      = (0.18, 0.16, 0.14, 0.95)
_RUST       = (0.72, 0.28, 0.08, 1.0)
_RUST_HOVER = (0.90, 0.38, 0.12, 1.0)
_DIRT_TEXT  = (0.82, 0.76, 0.65, 1.0)
_WORN_TEXT  = (0.55, 0.50, 0.43, 1.0)
_ERROR_RED  = (0.90, 0.25, 0.15, 1.0)
_ENTRY_BG   = (0.12, 0.10, 0.09, 1.0)


class NewProfileScreen:
    """First-run screen for nickname entry.

    Displayed when no local profile exists. After valid nick submission,
    saves profile and routes to MainMenu via app._show_screen().
    """

    def __init__(self, app) -> None:
        """Build the new profile screen.

        Args:
            app: ScrapyardApp instance (ShowBase subclass).
        """
        self.app = app
        self._elements: list = []
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        """Constructs all DirectGui elements."""
        # Subtitle (prompt)
        title = OnscreenText(
            text=t("new_profile.title"),
            pos=(0, 0.35),
            scale=0.09,
            fg=_DIRT_TEXT,
            shadow=(0.0, 0.0, 0.0, 0.8),
            align=TextNode.ACenter,
            mayChange=False,
        )
        self._elements.append(title)

        # Entry field background panel
        panel = DirectFrame(
            frameColor=_PLATE,
            frameSize=(-0.55, 0.55, -0.12, 0.12),
            pos=(0, 0, 0.05),
        )
        self._elements.append(panel)

        # Nick entry
        self._entry = DirectEntry(
            parent=panel,
            text="",
            scale=0.075,
            pos=(-0.48, 0, -0.04),
            width=12,
            pad=(0.2, 0.2),
            text_pos=(0.3, -0.01),
            numLines=1,
            focus=1,
            frameColor=_ENTRY_BG,
            text_fg=_DIRT_TEXT,
            initialText=t("new_profile.placeholder"),
            command=self._on_submit,
        )
        self._elements.append(self._entry)

        # Error label (hidden until validation fails)
        self._error_label = OnscreenText(
            text="",
            pos=(0, -0.15),
            scale=0.055,
            fg=_ERROR_RED,
            align=TextNode.ACenter,
            mayChange=True,
        )
        self._elements.append(self._error_label)

        # Submit button
        btn = DirectButton(
            text=t("new_profile.start"),
            scale=0.06,
            pos=(0, 0, -0.32),
            command=self._on_submit,
            frameColor=_RUST,
            frameSize=(-6.5, 6.5, -1.0, 1.3),
            text_fg=_DIRT_TEXT,
            relief="flat",
            pressEffect=True,
            text_align=TextNode.ACenter,
            pad=(0.4, 0.1),
        )
        btn.bind("enter", lambda _: self._animate_hover(btn, True))
        btn.bind("exit",  lambda _: self._animate_hover(btn, False))
        self._elements.append(btn)

        # Game title watermark (top-left)
        watermark = OnscreenText(
            text=t("game.title"),
            pos=(-1.28, 0.90),
            scale=0.065,
            fg=_RUST,
            align=TextNode.ALeft,
            mayChange=False,
        )
        self._elements.append(watermark)

    # ── Actions ───────────────────────────────────────────────────────────

    def _on_submit(self, text: str = "") -> None:
        """Validates and saves the nickname, then transitions to MainMenu.

        Args:
            text: Value passed by DirectEntry command callback (unused;
                  we read directly from self._entry).
        """
        nick = self._entry.get().strip()

        # Clear placeholder if still showing
        if nick == t("new_profile.placeholder"):
            nick = ""

        error_key = ProfileManager.validate_nick(nick)
        if error_key is not None:
            self._error_label.setText(t(error_key))
            return

        try:
            profile = ProfileManager.create(nick)
            self.app._profile = profile
            logger.info("Profile created: %s", nick)
            self.app._show_screen("main_menu")
        except ValueError as exc:
            self._error_label.setText(str(exc))
            logger.warning("Profile creation failed: %s", exc)

    # ── Hover animation ───────────────────────────────────────────────────

    @staticmethod
    def _animate_hover(btn: DirectButton, entering: bool) -> None:
        """Lerp button color on hover enter/exit.

        Args:
            btn: The button to animate.
            entering: True when mouse enters, False when it leaves.
        """
        color = (0.90, 0.38, 0.12, 1.0) if entering else (0.72, 0.28, 0.08, 1.0)
        btn["frameColor"] = color

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
