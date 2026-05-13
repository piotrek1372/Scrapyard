"""
FPVController — modular First-Person-View controller for Panda3D.

Architecture (SRP):
- InputState  : pure-data container for keyboard state and mouse deltas.
- FPVController : orchestrates camera rotation, movement physics, and
                  collision response.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

from panda3d.core import (
    CollisionHandlerPusher,
    CollisionNode,
    CollisionSphere,
    CollisionTraverser,
    NodePath,
    Vec3,
    WindowProperties,
)
from direct.showbase.ShowBase import ShowBase

logger = logging.getLogger("Scrapyard.FPV")


# ── Input State ───────────────────────────────────────────────────────────────

@dataclass
class InputState:
    """Pure-data container for keyboard state.

    This dataclass has no Panda3D dependencies and can be tested in
    isolation without a running application.
    """

    forward: bool = False
    backward: bool = False
    left: bool = False
    right: bool = False


# ── FPV Controller ────────────────────────────────────────────────────────────

class FPVController:
    """First-Person-View controller for Scrapyard.

    Responsibilities:
    - Window cursor capture / release (M_relative ↔ M_absolute).
    - Camera heading (yaw) and pitch from relative mouse deltas.
    - Vector-based WASD movement scaled by delta-time.
    - Gravity + ground-ray collision for terrain snapping.
    - Constraint box that prevents the player from leaving the tile grid.
    """

    # ── Class-level tuning constants ──────────────────────────────────────
    GRAVITY: float = -20.0
    """Downward acceleration in units/s²."""

    EYE_HEIGHT: float = 1.7
    """Camera offset above the player origin in units."""

    SPEED: float = 10.0
    """Horizontal movement speed in units/s."""

    MOUSE_SENSITIVITY: float = 50.0
    """Camera rotation per normalized mouse unit (degrees)."""

    PITCH_MIN: float = -89.0
    """Minimum vertical look angle (degrees)."""

    PITCH_MAX: float = 89.0
    """Maximum vertical look angle (degrees)."""

    FALL_RECOVERY_Z: float = 5.0
    """Z-coordinate used when the player falls below FALL_FLOOR."""

    FALL_FLOOR: float = -50.0
    """If player drops below this Z, teleport to FALL_RECOVERY_Z."""

    # ── Constructor ───────────────────────────────────────────────────────

    def __init__(
        self,
        base: ShowBase,
        start_pos: Vec3 = Vec3(0, 0, 5),
        bounds: float = 960.0,
    ) -> None:
        """Initialize the FPV controller.

        Args:
            base: The ShowBase application instance.
            start_pos: World-space position where the player spawns.
            bounds: Half-extent of the playable area in X and Y (units).
                    The player cannot move beyond ±bounds on either axis.
        """
        self.base = base
        self._bounds = bounds
        self.input = InputState()

        # Camera state (degrees)
        self._heading: float = 0.0
        self._pitch: float = 0.0

        # Vertical physics state
        self._velocity_z: float = 0.0

        # Tracks whether the cursor is captured
        self._input_locked: bool = False

        # ── Player node ───────────────────────────────────────────────
        self.player_np: NodePath = self.base.render.attachNewNode("player")
        self.player_np.setPos(start_pos)

        # ── Camera at eye level ───────────────────────────────────────
        self.base.camera.reparentTo(self.player_np)
        self.base.camera.setPos(0, 0, self.EYE_HEIGHT)
        self.base.camera.setHpr(0, 0, 0)

        self._setup_collisions()
        self._setup_input()

        # Lock the cursor immediately on startup.
        self.set_input_mode(locked=True)

        # sort=10 guarantees this task runs before main_update_task (sort=20)
        # so terrain and environment updates always read the camera position
        # that has already been advanced by the FPV controller this frame.
        self.base.taskMgr.add(self._update_task, "fpv_update_task", sort=10)
        logger.info(
            "FPVController ready — pos=%s bounds=±%.0f", start_pos, bounds
        )

    # ── Input mode ────────────────────────────────────────────────────────

    def set_input_mode(self, locked: bool) -> None:
        """Switch the cursor between captured and free modes.

        When releasing the cursor (locked=False) the pointer is explicitly
        moved to the window centre before applying M_absolute.  This
        prevents the OS cursor from materialising at the edge of the screen
        or on a secondary monitor — a side-effect of M_relative leaving the
        hardware cursor at an undefined position.

        Args:
            locked: True  → hide cursor, M_relative (game mode).
                    False → show cursor, M_absolute (menu / paused mode).
        """
        self._input_locked = locked
        props = WindowProperties()
        if locked:
            props.setCursorHidden(True)
            props.setMouseMode(WindowProperties.M_relative)
            logger.debug("Mouse captured (M_relative).")
        else:
            # Park the OS cursor at window centre before switching to
            # M_absolute so it appears in a predictable location.
            win = self.base.win
            cx: int = win.getXSize() // 2
            cy: int = win.getYSize() // 2
            win.movePointer(0, cx, cy)
            props.setCursorHidden(False)
            props.setMouseMode(WindowProperties.M_absolute)
            logger.debug("Mouse released (M_absolute) — cursor parked at centre.")
        self.base.win.requestProperties(props)

    # ── Private setup ─────────────────────────────────────────────────────

    def _setup_input(self) -> None:
        """Register key bindings for movement, Escape, and mouse re-lock."""
        bindings: Dict[str, tuple[str, bool]] = {
            "w":    ("forward",  True),
            "w-up": ("forward",  False),
            "s":    ("backward", True),
            "s-up": ("backward", False),
            "a":    ("left",     True),
            "a-up": ("left",     False),
            "d":    ("right",    True),
            "d-up": ("right",    False),
        }
        for event, (action, state) in bindings.items():
            self.base.accept(event, self._set_key, [action, state])

        # Escape triggers the pause screen via app.pause().
        self.base.accept("escape", self._on_escape)
        # Mouse1 re-locks the cursor when clicked in the game world.
        self.base.accept("mouse1", self._on_mouse1_click)


    def _set_key(self, action: str, state: bool) -> None:
        """Update a single boolean field on InputState.

        Args:
            action: Name of the InputState field (e.g. 'forward').
            state: New boolean value.
        """
        setattr(self.input, action, state)

    def _setup_collisions(self) -> None:
        """Initialize collision traverser and wall-pusher sphere.

        Reuses an existing cTrav on the ShowBase instance if one was
        already created by the application, to avoid duplicate traversers.

        Ground detection is NOT done via a collision ray because
        GeoMipTerrain's render mesh is invisible to CollisionTraverser.
        Instead, _apply_gravity() queries TerrainManager.get_height_at()
        directly from the stored PNMImage — O(1) and always accurate.
        """
        if not getattr(self.base, "cTrav", None):
            self.base.cTrav = CollisionTraverser("base_traverser")
            logger.debug("CollisionTraverser created by FPVController.")

        # ── Wall collision sphere ─────────────────────────────────────
        self.pusher = CollisionHandlerPusher()

        sphere_node = CollisionNode("player_sphere")
        sphere_node.addSolid(CollisionSphere(0, 0, 1.0, 0.5))
        sphere_node.setFromCollideMask(1)
        sphere_node.setIntoCollideMask(0)

        self.player_c_np = self.player_np.attachNewNode(sphere_node)
        self.pusher.addCollider(self.player_c_np, self.player_np)
        self.base.cTrav.addCollider(self.player_c_np, self.pusher)

    # ── Per-frame helpers ─────────────────────────────────────────────────

    def _rotate_camera(self) -> None:
        """Apply per-frame mouse deltas to yaw (player) and pitch (camera).

        Reads the raw pixel position via win.getPointer(0), computes the
        delta relative to the window centre, then immediately resets the
        OS cursor to the centre with win.movePointer().  This produces a
        true per-frame delta that is independent of cursor distance from
        centre — eliminating the "speed grows with distance" artefact that
        occurs when using getMouseX/Y() (which returns absolute position,
        not a delta, even under M_relative).
        """
        if not self._input_locked:
            return

        win = self.base.win
        ptr = win.getPointer(0)

        cx: int = win.getXSize() // 2
        cy: int = win.getYSize() // 2

        dx: float = float(ptr.getX() - cx)
        dy: float = float(ptr.getY() - cy)

        # Always re-centre so next frame's delta starts from zero.
        win.movePointer(0, cx, cy)

        if dx == 0.0 and dy == 0.0:
            return

        # Normalise by window half-size so sensitivity is resolution-
        # independent (matches the [-1, 1] range of the old getMouseX/Y).
        dx /= cx
        dy /= cy

        self._heading -= dx * self.MOUSE_SENSITIVITY
        self._pitch -= dy * self.MOUSE_SENSITIVITY
        self._pitch = max(self.PITCH_MIN, min(self.PITCH_MAX, self._pitch))

        # Heading drives the whole player body (yaw); pitch drives only
        # the camera node so strafing direction stays correct.
        self.player_np.setH(self._heading)
        self.base.camera.setP(self._pitch)

    def _apply_movement(self, dt: float) -> None:
        """Build and apply the WASD movement vector.

        Movement is expressed in the player's local coordinate frame so
        that forward always follows the current heading.

        Args:
            dt: Delta-time in seconds from the previous frame.
        """
        x: float = float(self.input.right) - float(self.input.left)
        y: float = float(self.input.forward) - float(self.input.backward)

        move = Vec3(x, y, 0)
        if move.lengthSquared() > 0:
            move.normalize()
            move *= self.SPEED * dt
            # setPos with a second NodePath argument moves in local space.
            self.player_np.setPos(self.player_np, move)

        # Clamp XY to the constraint box after applying the delta.
        clamped = self._clamp_position(self.player_np.getPos())
        self.player_np.setPos(clamped)

    def _apply_gravity(self, dt: float) -> None:
        """Integrate gravity and snap to ground via heightmap sampling.

        Replaces the former CollisionRay approach: GeoMipTerrain render
        meshes are invisible to CollisionTraverser, so the ray never hit
        the terrain.  Direct PNMImage sampling via
        TerrainManager.get_height_at() is O(1) and always accurate.

        Args:
            dt: Delta-time in seconds from the previous frame.
        """
        self._velocity_z += self.GRAVITY * dt
        self.player_np.setZ(self.player_np.getZ() + self._velocity_z * dt)

        terrain_mgr = getattr(self.base, "terrain_manager", None)
        if terrain_mgr is not None:
            surface_z: float = terrain_mgr.get_height_at(
                self.player_np.getX(), self.player_np.getY()
            )
            if self.player_np.getZ() <= surface_z:
                self.player_np.setZ(surface_z)
                self._velocity_z = 0.0

        if self.player_np.getZ() < self.FALL_FLOOR:
            logger.warning("Player fell below world floor — resetting Z.")
            self.player_np.setZ(self.FALL_RECOVERY_Z)
            self._velocity_z = 0.0

    def _clamp_position(self, pos: Vec3) -> Vec3:
        """Constrain the player to the playable tile grid.

        Args:
            pos: Unconstrained world-space position.

        Returns:
            Position with X and Y clamped to ±self._bounds.
        """
        return Vec3(
            max(-self._bounds, min(self._bounds, pos.x)),
            max(-self._bounds, min(self._bounds, pos.y)),
            pos.z,
        )

    # ── Frame task ────────────────────────────────────────────────────────

    def _update_task(self, task) -> int:
        """Per-frame task: camera rotation → movement → gravity.

        Execution order is intentional: rotate first so that movement
        direction is already up-to-date for this frame.

        Returns:
            task.cont to keep the task running.
        """
        dt: float = globalClock.getDt()  # type: ignore[name-defined]
        self._rotate_camera()
        self._apply_movement(dt)
        self._apply_gravity(dt)
        return task.cont

    # ── Public API ────────────────────────────────────────────────────────

    def get_pos(self) -> Vec3:
        """Return the player's current world-space position.

        Returns:
            Vec3 position of the player node.
        """
        return self.player_np.getPos()

    def pause(self) -> None:
        """Freezes FPV input and releases the mouse cursor.

        Called by ScrapyardApp.pause() before showing the pause overlay.
        """
        self.set_input_mode(locked=False)
        self.base.taskMgr.remove("fpv_update_task")
        logger.debug("FPVController paused.")

    def resume(self) -> None:
        """Restores FPV input and re-locks the mouse cursor.

        Called by ScrapyardApp.resume() after dismissing the pause overlay.
        """
        # Restart the update task (sort=10, same as constructor)
        self.base.taskMgr.add(
            self._update_task, "fpv_update_task", sort=10
        )
        self.set_input_mode(locked=True)
        logger.debug("FPVController resumed.")

    # ── Private event handlers ────────────────────────────────────────────

    def _on_escape(self) -> None:
        """Handles the Escape key: delegates pause to ScrapyardApp.

        ScrapyardApp.pause() handles state validation, overlay display,
        and cursor release — FPVController must not decide whether to pause.
        """
        pause_fn = getattr(self.base, "pause", None)
        if callable(pause_fn):
            pause_fn()
        else:
            # Fallback if called outside of ScrapyardApp context
            self.set_input_mode(locked=False)

    def _on_mouse1_click(self) -> None:
        """Re-locks the cursor on left-click, but only during PLAYING state.

        Prevents accidentally capturing the mouse while interacting with
        the pause overlay or other GUI elements.
        """
        from src.core.game_state import GameState
        state_mgr = getattr(self.base, "state_manager", None)
        if state_mgr is not None and state_mgr.is_in(GameState.PLAYING):
            self.set_input_mode(locked=True)
