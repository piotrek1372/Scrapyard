"""
SavesScreen — displays save slots in either LOAD or SAVE mode.

LOAD mode: clicking a card starts the game at the saved position.
SAVE mode: player types a name and creates a new save slot with screenshot.

Save cards show: thumbnail, name, nick, timestamp, delete button.
Supports unlimited saves (scrolled list when > 5 slots).
"""
from __future__ import annotations

import logging
from datetime import datetime

from direct.gui.DirectGui import (
    DirectButton,
    DirectEntry,
    DirectFrame,
    DirectLabel,
    DirectScrolledList,
    OnscreenText,
)
from panda3d.core import Filename, TextNode, Texture, TextureStage

from src.utils.i18n import t

logger = logging.getLogger("Scrapyard.UI.Saves")

# ── Palette ───────────────────────────────────────────────────────────────
_PLATE      = (0.16, 0.14, 0.12, 0.95)
_PLATE_DIM  = (0.12, 0.10, 0.09, 0.90)
_RUST       = (0.72, 0.28, 0.08, 1.0)
_RUST_HOVER = (0.90, 0.38, 0.12, 1.0)
_RED_DEL    = (0.65, 0.12, 0.08, 1.0)
_RED_HOVER  = (0.85, 0.18, 0.10, 1.0)
_DIRT_TEXT  = (0.82, 0.76, 0.65, 1.0)
_WORN_TEXT  = (0.50, 0.45, 0.38, 1.0)
_GREEN_OK   = (0.30, 0.70, 0.25, 1.0)


def _fmt_timestamp(iso_str: str) -> str:
    """Converts ISO 8601 to a short human-readable date/time string.

    Args:
        iso_str: ISO 8601 timestamp.

    Returns:
        Formatted string like '2026-05-13  15:30'.
    """
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d  %H:%M")
    except ValueError:
        return iso_str


class SavesScreen:
    """Save slot browser, dual-mode: load and save.

    Attributes:
        mode: 'load' to browse and load saves; 'save' to create a new save.
    """

    def __init__(self, app, mode: str = "load") -> None:
        """Build the saves screen.

        Args:
            app: ScrapyardApp instance.
            mode: 'load' or 'save'.
        """
        self.app = app
        self.mode = mode
        self._elements: list = []
        self._confirm_panel = None  # delete confirmation overlay
        self._status_label = None
        self._name_entry = None
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        """Constructs the saves list and optional save-name entry."""
        title_key = "saves.title_load" if self.mode == "load" else "saves.title_save"
        title = OnscreenText(
            text=t(title_key),
            pos=(0, 0.86),
            scale=0.09,
            fg=_RUST,
            shadow=(0, 0, 0, 0.8),
            align=TextNode.ACenter,
            mayChange=False,
        )
        self._elements.append(title)

        # ── Save-name entry (SAVE mode only) ──────────────────────────
        if self.mode == "save":
            entry_panel = DirectFrame(
                frameColor=_PLATE_DIM,
                frameSize=(-0.65, 0.65, -0.08, 0.08),
                pos=(0, 0, 0.68),
            )
            self._elements.append(entry_panel)

            self._name_entry = DirectEntry(
                parent=entry_panel,
                text="",
                scale=0.065,
                pos=(-0.55, 0, -0.035),
                width=16,
                numLines=1,
                focus=1,
                frameColor=(0.08, 0.07, 0.06, 1.0),
                text_fg=_DIRT_TEXT,
                initialText=t("saves.save_name_placeholder"),
            )
            self._elements.append(self._name_entry)

            save_btn = DirectButton(
                text=t("saves.save"),
                scale=0.065,
                pos=(0.52, 0, 0.68),
                command=self._on_create_save,
                frameColor=_RUST,
                text_fg=_DIRT_TEXT,
                relief="flat",
                pressEffect=True,
                text_align=TextNode.ACenter,
            )
            self._elements.append(save_btn)

        # ── Scrolled save list ────────────────────────────────────────
        saves = self.app.save_manager.list_saves()

        if not saves:
            no_saves = OnscreenText(
                text=t("saves.no_saves"),
                pos=(0, 0.10),
                scale=0.07,
                fg=_WORN_TEXT,
                align=TextNode.ACenter,
                mayChange=False,
            )
            self._elements.append(no_saves)
        else:
            items = [self._make_card(s) for s in saves]
            scroll = DirectScrolledList(
                frameSize=(-0.92, 0.92, -0.60, 0.48),
                pos=(0, 0, 0.06),
                items=items,
                numItemsVisible=3,
                forceHeight=0.24,
                itemFrame_frameColor=_PLATE_DIM,
                frameColor=_PLATE,
                decButton_pos=(-0.82, 0, 0.51),
                decButton_text="▲",
                decButton_scale=0.06,
                decButton_frameColor=_PLATE_DIM,
                decButton_text_fg=_DIRT_TEXT,
                incButton_pos=(-0.82, 0, -0.63),
                incButton_text="▼",
                incButton_scale=0.06,
                incButton_frameColor=_PLATE_DIM,
                incButton_text_fg=_DIRT_TEXT,
            )
            self._elements.append(scroll)

        # ── Status label ──────────────────────────────────────────────
        self._status_label = OnscreenText(
            text="",
            pos=(0, -0.74),
            scale=0.055,
            fg=_GREEN_OK,
            align=TextNode.ACenter,
            mayChange=True,
        )
        self._elements.append(self._status_label)

        # ── Back button ───────────────────────────────────────────────
        back_label = (
            "ui.back" if self.mode == "load" else "ui.back"
        )
        return_to = "main_menu" if self.mode == "load" else "pause"
        back_btn = DirectButton(
            text=t(back_label),
            scale=0.065,
            pos=(0, 0, -0.86),
            command=lambda: self.app._show_screen(return_to),
            frameColor=_PLATE_DIM,
            text_fg=_WORN_TEXT,
            relief="flat",
            pressEffect=True,
            text_align=TextNode.ACenter,
        )
        self._elements.append(back_btn)

    def _make_card(self, save_meta) -> DirectFrame:
        """Creates a single save card widget.

        Args:
            save_meta: SaveMeta instance.

        Returns:
            DirectFrame representing the save card.
        """
        card = DirectFrame(
            frameColor=_PLATE_DIM,
            frameSize=(-0.88, 0.88, -0.10, 0.10),
        )

        # Thumbnail (if available)
        thumb_path = self.app.save_manager.get_screenshot_path(save_meta.id)
        if thumb_path is not None:
            try:
                tex = self.app.loader.loadTexture(
                    Filename.fromOsSpecific(str(thumb_path))
                )
                if tex:
                    from direct.gui.DirectGui import DirectFrame as _DF
                    thumb = _DF(
                        parent=card,
                        frameColor=(1, 1, 1, 1),
                        frameSize=(-0.12, 0.12, -0.085, 0.085),
                        frameTexture=tex,
                        pos=(-0.72, 0, 0),
                    )
            except Exception as exc:
                logger.debug("Thumbnail load failed for %s: %s", save_meta.id, exc)

        # Name
        DirectLabel(
            parent=card,
            text=save_meta.name,
            scale=0.058,
            pos=(-0.46, 0, 0.03),
            text_fg=_DIRT_TEXT,
            frameColor=(0, 0, 0, 0),
            text_align=TextNode.ALeft,
        )

        # Nick + timestamp
        DirectLabel(
            parent=card,
            text=f"{save_meta.nick}  •  {_fmt_timestamp(save_meta.timestamp)}",
            scale=0.042,
            pos=(-0.46, 0, -0.04),
            text_fg=_WORN_TEXT,
            frameColor=(0, 0, 0, 0),
            text_align=TextNode.ALeft,
        )

        # Action button (Load or label)
        if self.mode == "load":
            action_btn = DirectButton(
                parent=card,
                text=t("saves.load"),
                scale=0.055,
                pos=(0.65, 0, 0.03),
                command=self._on_load,
                extraArgs=[save_meta.id],
                frameColor=_RUST,
                text_fg=_DIRT_TEXT,
                relief="flat",
                pressEffect=True,
                text_align=TextNode.ACenter,
            )

        # Delete button (always)
        del_btn = DirectButton(
            parent=card,
            text=t("saves.delete"),
            scale=0.048,
            pos=(0.65, 0, -0.05),
            command=self._on_delete_request,
            extraArgs=[save_meta.id],
            frameColor=_RED_DEL,
            text_fg=_DIRT_TEXT,
            relief="flat",
            pressEffect=True,
            text_align=TextNode.ACenter,
        )

        return card

    # ── Actions ───────────────────────────────────────────────────────────

    def _on_load(self, save_id: str) -> None:
        """Starts the game and restores the selected save.

        Args:
            save_id: UUID of the save slot to load.
        """
        logger.info("Loading save: %s", save_id)
        self.app.start_game(load_save_id=save_id)

    def _on_create_save(self) -> None:
        """Creates a new save slot in SAVE mode."""
        if self._name_entry is None:
            return
        name = self._name_entry.get().strip()
        placeholder = t("saves.save_name_placeholder")
        if name == placeholder:
            name = ""

        if self._status_label:
            self._status_label.setText(t("saves.saving"))

        try:
            meta = self.app.save_manager.save_game(name, self.app)
            if self._status_label:
                self._status_label.setText(t("saves.saved"))
            logger.info("New save created: '%s'", meta.name)
            # Rebuild screen to show the new card
            self.app._show_screen("saves_save")
        except Exception as exc:
            logger.error("Save failed: %s", exc)
            if self._status_label:
                self._status_label.setText(str(exc))

    def _on_delete_request(self, save_id: str) -> None:
        """Shows a small inline confirmation before deleting.

        Args:
            save_id: UUID of the save to delete.
        """
        # Build a simple confirmation overlay
        if self._confirm_panel is not None:
            try:
                self._confirm_panel.destroy()
            except Exception:
                pass

        panel = DirectFrame(
            frameColor=_PLATE,
            frameSize=(-0.45, 0.45, -0.18, 0.18),
            pos=(0, 0, 0),
        )
        self._elements.append(panel)
        self._confirm_panel = panel

        DirectLabel(
            parent=panel,
            text=t("saves.confirm_delete"),
            scale=0.060,
            pos=(0, 0, 0.08),
            text_fg=_DIRT_TEXT,
            frameColor=(0, 0, 0, 0),
            text_align=TextNode.ACenter,
        )
        DirectButton(
            parent=panel,
            text=t("saves.yes"),
            scale=0.065,
            pos=(-0.18, 0, -0.07),
            command=self._on_delete_confirm,
            extraArgs=[save_id],
            frameColor=_RED_DEL,
            text_fg=_DIRT_TEXT,
            relief="flat",
            pressEffect=True,
        )
        DirectButton(
            parent=panel,
            text=t("saves.no"),
            scale=0.065,
            pos=(0.18, 0, -0.07),
            command=self._dismiss_confirm,
            frameColor=_PLATE_DIM,
            text_fg=_WORN_TEXT,
            relief="flat",
            pressEffect=True,
        )

    def _on_delete_confirm(self, save_id: str) -> None:
        """Deletes the save and rebuilds the screen.

        Args:
            save_id: UUID of the confirmed deletion target.
        """
        self.app.save_manager.delete_save(save_id)
        logger.info("Save deleted: %s", save_id)
        # Rebuild screen
        screen_name = "saves_load" if self.mode == "load" else "saves_save"
        self.app._show_screen(screen_name)

    def _dismiss_confirm(self) -> None:
        """Hides the confirmation panel without deleting."""
        if self._confirm_panel is not None:
            try:
                self._confirm_panel.destroy()
            except Exception:
                pass
            self._confirm_panel = None

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
