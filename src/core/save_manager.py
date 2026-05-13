"""
SaveManager — manages unlimited local save slots for Scrapyard.

Each save is stored in data/saves/<uuid>/ with:
  - meta.json       : serialized SaveMeta (id, name, timestamp, nick,
                      position, balance, seed)
  - screenshot.png  : 320×180 thumbnail captured from the game window

Dependencies: pathlib, json, uuid, shutil, panda3d.core (PNMImage, Filename)
"""
from __future__ import annotations

import json
import logging
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("Scrapyard.SaveManager")


@dataclass
class SaveMeta:
    """Metadata for a single save slot.

    Attributes:
        id: UUID string used as the directory name.
        name: Human-readable save name provided by the player.
        timestamp: ISO 8601 creation timestamp.
        nick: Player nickname at the time of saving.
        position: World-space player position [x, y, z].
        balance: Player balance at the time of saving.
        seed: Terrain generation seed (reserved for future use).
    """

    id: str
    name: str
    timestamp: str
    nick: str
    position: list[float]
    balance: int
    seed: int


class SaveManager:
    """Manages creation, loading, listing, and deletion of save files.

    Save directory layout::

        data/saves/<uuid>/
            meta.json
            screenshot.png   (320×180, optional — captured before overlay)
    """

    SCREENSHOT_W: int = 320
    SCREENSHOT_H: int = 180

    def __init__(self, saves_dir: Path) -> None:
        """Initialize with the path to the saves root directory.

        Args:
            saves_dir: Absolute path to data/saves/.
        """
        self._dir = saves_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────

    def list_saves(self) -> List[SaveMeta]:
        """Returns all saves sorted by timestamp descending (newest first).

        Returns:
            List of SaveMeta instances; empty list if no saves exist.
        """
        metas: List[SaveMeta] = []
        for slot_dir in self._dir.iterdir():
            if not slot_dir.is_dir():
                continue
            meta = self._load_meta(slot_dir)
            if meta is not None:
                metas.append(meta)
        metas.sort(key=lambda m: m.timestamp, reverse=True)
        return metas

    def save_game(
        self,
        name: str,
        app,  # ScrapyardApp — circular import avoided via duck-typing
    ) -> SaveMeta:
        """Creates a new save slot from the current game state.

        Screenshot is captured BEFORE any overlay is shown so the
        thumbnail displays the in-game world view.

        Args:
            name: Human-readable save name.
            app: Running ScrapyardApp instance (ShowBase subclass).

        Returns:
            SaveMeta for the newly created save slot.
        """
        save_id = str(uuid.uuid4())
        slot_dir = self._dir / save_id
        slot_dir.mkdir(parents=True, exist_ok=True)

        # Screenshot must be first — no overlays yet.
        self._capture_screenshot(app, slot_dir)

        # Player position
        pos: list[float] = [0.0, 0.0, 5.0]
        fpv = getattr(app, "fpv_controller", None)
        if fpv is not None:
            p = fpv.get_pos()
            pos = [float(p.x), float(p.y), float(p.z)]

        # Profile data
        nick = "Unknown"
        balance = 0
        profile = getattr(app, "_profile", None)
        if profile is not None:
            nick = profile.nick
            balance = profile.balance

        # Terrain seed (stored for future use)
        seed: int = getattr(
            getattr(app, "terrain_manager", None), "seed", 0
        )

        meta = SaveMeta(
            id=save_id,
            name=name.strip() or "Quick Save",
            timestamp=datetime.now(timezone.utc).isoformat(),
            nick=nick,
            position=pos,
            balance=balance,
            seed=seed,
        )
        self._write_meta(slot_dir, meta)
        logger.info("Game saved: '%s' (id=%s)", meta.name, save_id)
        return meta

    def load_game(self, save_id: str, app) -> bool:
        """Restores game state from a save slot.

        Currently restores: player position and balance.
        Terrain seed restoration is a planned future extension.

        Args:
            save_id: UUID string of the save slot to load.
            app: Running ScrapyardApp instance.

        Returns:
            True on success, False if the save is not found or corrupt.
        """
        slot_dir = self._dir / save_id
        meta = self._load_meta(slot_dir)
        if meta is None:
            logger.error("Save not found or corrupt: %s", save_id)
            return False

        fpv = getattr(app, "fpv_controller", None)
        if fpv is not None:
            from panda3d.core import Vec3
            fpv.player_np.setPos(Vec3(*meta.position))
            logger.info(
                "Position restored to %s from save '%s'",
                meta.position,
                meta.name,
            )

        profile = getattr(app, "_profile", None)
        if profile is not None:
            profile.balance = meta.balance

        return True

    def delete_save(self, save_id: str) -> None:
        """Deletes a save slot directory and all its contents.

        Args:
            save_id: UUID string of the save to delete.
        """
        slot_dir = self._dir / save_id
        if slot_dir.exists():
            shutil.rmtree(slot_dir)
            logger.info("Save deleted: %s", save_id)
        else:
            logger.warning(
                "Delete requested but save not found: %s", save_id
            )

    def get_screenshot_path(self, save_id: str) -> Optional[Path]:
        """Returns the Path to a save's screenshot if it exists.

        Args:
            save_id: UUID string.

        Returns:
            Absolute Path to screenshot.png, or None if not present.
        """
        path = self._dir / save_id / "screenshot.png"
        return path if path.exists() else None

    # ── Private helpers ───────────────────────────────────────────────────

    def _capture_screenshot(self, app, slot_dir: Path) -> None:
        """Captures a full-resolution screenshot and scales to thumbnail.

        Uses Panda3D's PNMImage API. gaussianFilterFrom() produces a
        high-quality downsample without aliasing.

        Args:
            app: ShowBase instance providing the active window.
            slot_dir: Directory where screenshot.png will be written.
        """
        try:
            from panda3d.core import Filename, PNMImage

            full = PNMImage()
            if not app.win.getScreenshot(full):
                logger.warning(
                    "win.getScreenshot() returned False — skipping thumbnail."
                )
                return

            thumb = PNMImage(self.SCREENSHOT_W, self.SCREENSHOT_H)
            thumb.gaussianFilterFrom(1.0, full)

            out_path = slot_dir / "screenshot.png"
            if not thumb.write(Filename.fromOsSpecific(str(out_path))):
                logger.warning("PNMImage.write() failed for %s", out_path)
            else:
                logger.debug("Screenshot thumbnail saved: %s", out_path)
        except Exception as exc:
            logger.error("Screenshot capture failed: %s", exc)

    def _load_meta(self, slot_dir: Path) -> Optional[SaveMeta]:
        """Loads and deserializes meta.json from a slot directory.

        Args:
            slot_dir: Path to the save slot directory.

        Returns:
            SaveMeta, or None if the file is missing or corrupt.
        """
        meta_path = slot_dir / "meta.json"
        if not meta_path.exists():
            return None
        try:
            with meta_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return SaveMeta(**data)
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.error(
                "Corrupt meta.json in '%s': %s", slot_dir.name, exc
            )
            return None

    def _write_meta(self, slot_dir: Path, meta: SaveMeta) -> None:
        """Serializes and writes meta.json to a slot directory.

        Args:
            slot_dir: Path to the save slot directory.
            meta: SaveMeta to persist.
        """
        meta_path = slot_dir / "meta.json"
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(asdict(meta), f, indent=2, ensure_ascii=False)
