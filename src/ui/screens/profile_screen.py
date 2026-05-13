"""
ProfileScreen — displays and edits the local player profile.

Shows: nick (editable), balance (read-only), created_at, total_playtime.
Nick changes are validated before saving.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

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

logger = logging.getLogger("Scrapyard.UI.Profile")

# ── Palette ───────────────────────────────────────────────────────────────
_PLATE      = (0.16, 0.14, 0.12, 0.95)
_PLATE_DIM  = (0.12, 0.10, 0.09, 0.90)
_RUST       = (0.72, 0.28, 0.08, 1.0)
_DIRT_TEXT  = (0.82, 0.76, 0.65, 1.0)
_WORN_TEXT  = (0.50, 0.45, 0.38, 1.0)
_AMBER      = (0.95, 0.60, 0.15, 1.0)
_GREEN_OK   = (0.30, 0.70, 0.25, 1.0)
_ERROR_RED  = (0.90, 0.25, 0.15, 1.0)
_ENTRY_BG   = (0.10, 0.09, 0.08, 1.0)


def _format_playtime(seconds: float) -> str:
    """Converts total seconds to HH:MM:SS string.

    Args:
        seconds: Total playtime in seconds.

    Returns:
        Human-readable duration string.
    """
    td = timedelta(seconds=int(seconds))
    total_h = td.seconds // 3600 + td.days * 24
    m = (td.seconds % 3600) // 60
    s = td.seconds % 60
    return f"{total_h:02d}:{m:02d}:{s:02d}"


def _format_date(iso_str: str) -> str:
    """Formats an ISO 8601 timestamp to a locale-friendly date string.

    Args:
        iso_str: ISO 8601 string from Profile.created_at.

    Returns:
        Date in YYYY-MM-DD format, or original string on parse failure.
    """
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return iso_str


class ProfileScreen:
    """Player profile viewer and editor.

    Displayed from MainMenuScreen. Nick is editable; all other fields
    are read-only. Changes are saved on button press.
    """

    def __init__(self, app) -> None:
        """Build the profile screen.

        Args:
            app: ScrapyardApp instance.
        """
        self.app = app
        self._elements: list = []
        self._status_label = None
        self._nick_entry = None
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        """Constructs all DirectGui elements."""
        profile = getattr(self.app, "_profile", None)

        # Title
        title = OnscreenText(
            text=t("profile.title"),
            pos=(0, 0.82),
            scale=0.10,
            fg=_RUST,
            shadow=(0, 0, 0, 0.8),
            align=TextNode.ACenter,
            mayChange=False,
        )
        self._elements.append(title)

        # Info card
        card = DirectFrame(
            frameColor=_PLATE,
            frameSize=(-0.65, 0.65, -0.52, 0.52),
            pos=(0, 0, 0.15),
        )
        self._elements.append(card)

        y = 0.38

        # Nick (editable)
        self._add_row(card, t("profile.nick_label"), y, is_label=False)
        self._nick_entry = DirectEntry(
            parent=card,
            text=profile.nick if profile else "",
            scale=0.065,
            pos=(0.02, 0, y - 0.04),
            width=16,
            numLines=1,
            frameColor=_ENTRY_BG,
            text_fg=_DIRT_TEXT,
        )
        self._elements.append(self._nick_entry)
        y -= 0.18

        # Balance (read-only)
        balance_str = (
            f"${profile.balance:,}" if profile else "$0"
        )
        self._add_row(card, t("profile.balance_label"), y, value=balance_str)
        y -= 0.18

        # Created at
        created_str = (
            _format_date(profile.created_at) if profile else "—"
        )
        self._add_row(card, t("profile.created_label"), y, value=created_str)
        y -= 0.18

        # Playtime
        playtime_str = (
            _format_playtime(profile.total_playtime_s) if profile else "00:00:00"
        )
        self._add_row(card, t("profile.playtime_label"), y, value=playtime_str)

        # Status label
        self._status_label = OnscreenText(
            text="",
            pos=(0, -0.52),
            scale=0.055,
            fg=_GREEN_OK,
            align=TextNode.ACenter,
            mayChange=True,
        )
        self._elements.append(self._status_label)

        # Save button
        save_btn = DirectButton(
            text=t("profile.save"),
            scale=0.072,
            pos=(-0.18, 0, -0.72),
            command=self._on_save,
            frameColor=_RUST,
            text_fg=_DIRT_TEXT,
            relief="flat",
            pressEffect=True,
            text_align=TextNode.ACenter,
        )
        self._elements.append(save_btn)

        # Back button
        back_btn = DirectButton(
            text=t("profile.back"),
            scale=0.065,
            pos=(0.30, 0, -0.72),
            command=self._on_back,
            frameColor=_PLATE_DIM,
            text_fg=_WORN_TEXT,
            relief="flat",
            pressEffect=True,
            text_align=TextNode.ACenter,
        )
        self._elements.append(back_btn)

    def _add_row(
        self,
        parent,
        label: str,
        y: float,
        value: str = "",
        is_label: bool = True,
    ) -> None:
        """Adds a label + value row to the card.

        Args:
            parent: Parent DirectGui node.
            label: Row label string.
            y: Vertical offset within the card.
            value: Read-only value string (ignored when is_label=False).
            is_label: If False, skips creating the value widget
                      (caller inserts a DirectEntry instead).
        """
        lbl = DirectLabel(
            parent=parent,
            text=label,
            scale=0.052,
            pos=(-0.58, 0, y),
            text_fg=_WORN_TEXT,
            frameColor=(0, 0, 0, 0),
            text_align=TextNode.ALeft,
        )
        self._elements.append(lbl)

        if is_label and value:
            val = DirectLabel(
                parent=parent,
                text=value,
                scale=0.062,
                pos=(0.02, 0, y),
                text_fg=_DIRT_TEXT,
                frameColor=(0, 0, 0, 0),
                text_align=TextNode.ALeft,
            )
            self._elements.append(val)

    # ── Actions ───────────────────────────────────────────────────────────

    def _on_save(self) -> None:
        """Validates and saves the updated nick."""
        if self._nick_entry is None or self.app._profile is None:
            return

        new_nick = self._nick_entry.get().strip()
        error_key = ProfileManager.validate_nick(new_nick)

        if error_key is not None:
            if self._status_label:
                self._status_label["fg"] = _ERROR_RED
                self._status_label.setText(t(error_key))
            return

        self.app._profile.nick = new_nick
        ProfileManager.save(self.app._profile)

        if self._status_label:
            self._status_label["fg"] = _GREEN_OK
            self._status_label.setText(t("profile.saved"))
        logger.info("Profile updated: nick=%s", new_nick)

    def _on_back(self) -> None:
        """Returns to the main menu."""
        self.app._show_screen("main_menu")

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
