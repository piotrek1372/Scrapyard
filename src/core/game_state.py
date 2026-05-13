"""
Game state management for Scrapyard.

Defines the GameState enum and StateManager that coordinates transitions
between menu, playing, paused, settings, profile, and saves screens.
"""
from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Callable, Dict, Optional

logger = logging.getLogger("Scrapyard.GameState")


class GameState(Enum):
    """All possible states of the Scrapyard application."""

    MAIN_MENU = auto()
    NEW_PROFILE = auto()
    PROFILE = auto()
    SETTINGS = auto()
    SAVES_LOAD = auto()   # opens saves screen in load mode
    SAVES_SAVE = auto()   # opens saves screen in save mode
    PLAYING = auto()
    PAUSED = auto()


class StateManager:
    """Manages game state transitions with optional per-state callbacks.

    Screens register enter/exit callbacks when they are created.
    StateManager calls them in order: exit(old) → enter(new).

    Usage::

        sm = StateManager()
        sm.register(GameState.MAIN_MENU, on_enter=show_menu, on_exit=hide_menu)
        sm.transition(GameState.MAIN_MENU)
    """

    def __init__(self) -> None:
        """Initializes StateManager in MAIN_MENU state with no callbacks."""
        self._state: GameState = GameState.MAIN_MENU
        self._enter_callbacks: Dict[GameState, Callable[[], None]] = {}
        self._exit_callbacks: Dict[GameState, Callable[[], None]] = {}

    @property
    def state(self) -> GameState:
        """Current active game state."""
        return self._state

    def register(
        self,
        state: GameState,
        on_enter: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
    ) -> None:
        """Register enter/exit callbacks for a given state.

        Args:
            state: The GameState to register callbacks for.
            on_enter: Called when transitioning INTO this state.
            on_exit: Called when transitioning OUT OF this state.
        """
        if on_enter is not None:
            self._enter_callbacks[state] = on_enter
        if on_exit is not None:
            self._exit_callbacks[state] = on_exit

    def transition(self, new_state: GameState) -> None:
        """Execute a state transition.

        Calls the exit callback of the current state, then the enter
        callback of the new state. No-ops if already in new_state.

        Args:
            new_state: The target GameState to transition into.
        """
        if new_state == self._state:
            logger.debug(
                "StateManager: already in %s, skipping.", new_state.name
            )
            return

        logger.info(
            "State transition: %s → %s",
            self._state.name,
            new_state.name,
        )

        exit_cb = self._exit_callbacks.get(self._state)
        if exit_cb:
            exit_cb()

        self._state = new_state

        enter_cb = self._enter_callbacks.get(new_state)
        if enter_cb:
            enter_cb()

    def is_in(self, *states: GameState) -> bool:
        """Returns True if the current state is any of the given states.

        Args:
            *states: One or more GameState values to check against.

        Returns:
            True if self._state is among the provided states.
        """
        return self._state in states
