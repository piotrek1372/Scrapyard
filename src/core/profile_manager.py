"""
ProfileManager — manages the local player profile for Scrapyard.

Profile is persisted as JSON in ~/.scrapyard/profile.json.
Fields: nick, balance, created_at (ISO 8601), total_playtime_s.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("Scrapyard.Profile")

_PROFILE_DIR: Path = Path.home() / ".scrapyard"
_PROFILE_PATH: Path = _PROFILE_DIR / "profile.json"

NICK_MIN_LENGTH: int = 3
NICK_MAX_LENGTH: int = 20


@dataclass
class Profile:
    """Represents the local player profile.

    Attributes:
        nick: Player display name (3–20 characters).
        balance: In-game currency amount (non-negative).
        created_at: ISO 8601 timestamp of account creation.
        total_playtime_s: Cumulative playtime in seconds.
    """

    nick: str
    balance: int = 0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    total_playtime_s: float = 0.0


class ProfileManager:
    """Loads, saves, creates, and validates the local player profile.

    All methods are static — no instance state is maintained.
    File location: ~/.scrapyard/profile.json
    """

    @staticmethod
    def exists() -> bool:
        """Returns True if a profile file is present on disk.

        Returns:
            bool: True when profile.json exists at the expected path.
        """
        return _PROFILE_PATH.exists()

    @staticmethod
    def load() -> Optional[Profile]:
        """Loads the profile from disk.

        Returns:
            Profile instance, or None if the file is missing or corrupt.
        """
        if not _PROFILE_PATH.exists():
            return None
        try:
            with _PROFILE_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return Profile(**data)
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.error("Failed to load profile: %s", exc)
            return None

    @staticmethod
    def save(profile: Profile) -> None:
        """Saves the profile to disk.

        Args:
            profile: Profile instance to persist.
        """
        try:
            _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            with _PROFILE_PATH.open("w", encoding="utf-8") as f:
                json.dump(asdict(profile), f, indent=2, ensure_ascii=False)
            logger.info("Profile saved: %s", profile.nick)
        except OSError as exc:
            logger.error("Failed to save profile: %s", exc)

    @staticmethod
    def create(nick: str) -> Profile:
        """Creates and persists a new profile.

        Args:
            nick: Player nickname (3–20 characters, leading/trailing
                  whitespace is stripped before validation).

        Returns:
            Newly created and saved Profile.

        Raises:
            ValueError: If nick length is out of the allowed range.
        """
        nick = nick.strip()
        if len(nick) < NICK_MIN_LENGTH:
            raise ValueError(
                f"Nickname too short: {len(nick)} < {NICK_MIN_LENGTH}"
            )
        if len(nick) > NICK_MAX_LENGTH:
            raise ValueError(
                f"Nickname too long: {len(nick)} > {NICK_MAX_LENGTH}"
            )
        profile = Profile(nick=nick)
        ProfileManager.save(profile)
        logger.info("New profile created: %s", nick)
        return profile

    @staticmethod
    def validate_nick(nick: str) -> Optional[str]:
        """Validates a nick string.

        Args:
            nick: Nickname to validate (whitespace is stripped first).

        Returns:
            An i18n error key (e.g. 'new_profile.error_short') if
            invalid, or None if the nick is acceptable.
        """
        stripped = nick.strip()
        if len(stripped) < NICK_MIN_LENGTH:
            return "new_profile.error_short"
        if len(stripped) > NICK_MAX_LENGTH:
            return "new_profile.error_long"
        return None
