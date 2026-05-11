"""
HUD module — Panda3D DirectGui overlay for Scrapyard.

Manages all 2D interface elements: title screen, loot button,
item info panel, and navigation.
"""

from direct.gui.DirectGui import (
    DirectButton, DirectFrame, DirectLabel, OnscreenText
)
from panda3d.core import TextNode, LVecBase4f

from src.utils.i18n import t, t_item, t_category


# ── Color palette ─────────────────────────────────────────────────────────

COL_BG = (0.12, 0.12, 0.14, 0.85)
COL_BG_SOLID = (0.12, 0.12, 0.14, 1.0)
COL_ACCENT = (0.95, 0.6, 0.15, 1.0)       # warm orange
COL_ACCENT_HOVER = (1.0, 0.7, 0.25, 1.0)
COL_TEXT = (0.92, 0.92, 0.90, 1.0)
COL_TEXT_DIM = (0.6, 0.6, 0.58, 1.0)
COL_VALUE = (0.3, 0.85, 0.4, 1.0)          # green for value
COL_CONDITION = (0.85, 0.3, 0.3, 1.0)      # red for low condition
COL_CONDITION_OK = (0.3, 0.85, 0.4, 1.0)   # green for good condition


class HUD:
    """Manages all 2D GUI elements for the Scrapyard game."""

    def __init__(self, app):
        """
        Args:
            app: Reference to ScrapyardApp (ShowBase subclass).
        """
        self.app = app
        self._elements = []  # track all GUI nodes for cleanup

        self._build_title_screen()

    # ── Title screen ──────────────────────────────────────────────────────

    def _build_title_screen(self):
        """Shows game title + Loot button."""
        self.clear()

        # Title
        title = OnscreenText(
            text=t("game.title"),
            pos=(0, 0.55),
            scale=0.18,
            fg=COL_ACCENT,
            shadow=(0, 0, 0, 0.7),
            align=TextNode.ACenter,
            mayChange=False,
        )
        self._elements.append(title)

        # Subtitle
        subtitle = OnscreenText(
            text=t("game.overlooking"),
            pos=(0, 0.40),
            scale=0.06,
            fg=COL_TEXT_DIM,
            align=TextNode.ACenter,
            mayChange=False,
        )
        self._elements.append(subtitle)

        # Loot button
        loot_btn = DirectButton(
            text=t("ui.loot_button"),
            scale=0.12,
            pos=(0, 0, 0.05),
            command=self._on_loot,
            text_fg=COL_BG_SOLID,
            frameColor=COL_ACCENT,
            relief="flat",
            pressEffect=True,
            text_align=TextNode.ACenter,
        )
        self._elements.append(loot_btn)

        # Language indicator
        lang_label = OnscreenText(
            text=t("ui.language", lang=self.app.i18n.get_language().upper()),
            pos=(-1.3, -0.92),
            scale=0.045,
            fg=COL_TEXT_DIM,
            align=TextNode.ALeft,
            mayChange=False,
        )
        self._elements.append(lang_label)

        # Quit button
        quit_btn = DirectButton(
            text=t("ui.quit"),
            scale=0.06,
            pos=(1.15, 0, -0.92),
            command=self.app.userExit,
            text_fg=COL_TEXT_DIM,
            frameColor=(0.2, 0.2, 0.22, 0.8),
            relief="flat",
            text_align=TextNode.ACenter,
        )
        self._elements.append(quit_btn)

    # ── Item inspect screen ───────────────────────────────────────────────

    def show_item(self, item):
        """Shows item info panel after looting.

        Args:
            item: Item instance from Scrapyard.loot()
        """
        self.clear()

        # Item name (translated)
        name_text = OnscreenText(
            text=t_item(item.name),
            pos=(0, 0.82),
            scale=0.11,
            fg=COL_ACCENT,
            shadow=(0, 0, 0, 0.7),
            align=TextNode.ACenter,
            mayChange=False,
        )
        self._elements.append(name_text)

        # Info panel background
        panel = DirectFrame(
            frameColor=COL_BG,
            frameSize=(-0.55, 0.55, -0.35, 0.35),
            pos=(-0.85, 0, 0.0),
        )
        self._elements.append(panel)

        # Category
        y_pos = 0.22
        cat_text = OnscreenText(
            text=t("ui.item_category", category=t_category(item.category)),
            pos=(0, y_pos),
            scale=0.055,
            fg=COL_TEXT_DIM,
            align=TextNode.ACenter,
            parent=panel,
            mayChange=False,
        )
        self._elements.append(cat_text)

        # Value
        y_pos -= 0.16
        val_color = COL_VALUE
        val_text = OnscreenText(
            text=t("ui.item_value", value=item.value),
            pos=(0, y_pos),
            scale=0.065,
            fg=val_color,
            align=TextNode.ACenter,
            parent=panel,
            mayChange=False,
        )
        self._elements.append(val_text)

        # Condition
        y_pos -= 0.16
        cond_pct = int(item.condition * 100)
        cond_color = COL_CONDITION_OK if cond_pct >= 50 else COL_CONDITION
        cond_text = OnscreenText(
            text=t("ui.item_condition", condition=cond_pct),
            pos=(0, y_pos),
            scale=0.065,
            fg=cond_color,
            align=TextNode.ACenter,
            parent=panel,
            mayChange=False,
        )
        self._elements.append(cond_text)

        # No-model indicator
        if not item.has_model():
            y_pos -= 0.18
            no_model = OnscreenText(
                text=t("ui.no_model"),
                pos=(0, y_pos),
                scale=0.045,
                fg=COL_TEXT_DIM,
                align=TextNode.ACenter,
                parent=panel,
                mayChange=False,
            )
            self._elements.append(no_model)

        # Search again button
        search_btn = DirectButton(
            text=t("ui.search_again"),
            scale=0.08,
            pos=(0, 0, -0.82),
            command=self._on_loot,
            text_fg=COL_BG_SOLID,
            frameColor=COL_ACCENT,
            relief="flat",
            pressEffect=True,
            text_align=TextNode.ACenter,
        )
        self._elements.append(search_btn)

        # Back button
        back_btn = DirectButton(
            text=t("ui.back"),
            scale=0.06,
            pos=(-1.15, 0, -0.92),
            command=self._on_back,
            text_fg=COL_TEXT_DIM,
            frameColor=(0.2, 0.2, 0.22, 0.8),
            relief="flat",
            text_align=TextNode.ACenter,
        )
        self._elements.append(back_btn)

        # Quit button
        quit_btn = DirectButton(
            text=t("ui.quit"),
            scale=0.06,
            pos=(1.15, 0, -0.92),
            command=self.app.userExit,
            text_fg=COL_TEXT_DIM,
            frameColor=(0.2, 0.2, 0.22, 0.8),
            relief="flat",
            text_align=TextNode.ACenter,
        )
        self._elements.append(quit_btn)

    # ── Actions ───────────────────────────────────────────────────────────

    def _on_loot(self):
        """Triggers a loot action in the app."""
        self.app.do_loot()

    def _on_back(self):
        """Returns to the title screen."""
        self.app.show_title()

    # ── Cleanup ───────────────────────────────────────────────────────────

    def clear(self):
        """Removes all current GUI elements."""
        for elem in self._elements:
            try:
                elem.destroy()
            except Exception:
                try:
                    elem.removeNode()
                except Exception:
                    pass
        self._elements.clear()
