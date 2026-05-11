import random
from typing import Any, Dict, List

from src.utils.path_manager import PathManager
from src.utils.item_validator import ItemValidator
from src.core.item import Item


class EmptyLootPoolError(Exception):
    """Raised when the loot pool has no valid items."""
    pass


class Scrapyard:
    """Represents the player's primary source of items and money."""

    def __init__(self, items: List[Any] = None) -> None:
        """Initializes Scrapyard with a validated pool of items.
        
        Loads raw items database, validates each item for 3D model
        existence and translation completeness, and stores the valid ones.
        """
        self.available_items: List[Any] = items if items is not None else []
        
        raw_db: List[Dict[str, Any]] = PathManager().load_items_db()
        validator = ItemValidator()
        self.valid_items: List[Dict[str, Any]] = validator.get_valid_items(
            raw_db
        )

    def loot(self) -> Item:
        """Generates a random item for the user from the validated pool.
        
        Raises:
            EmptyLootPoolError: If no items passed validation.
            
        Returns:
            Item: The generated item ready for gameplay.
        """
        if not self.valid_items:
            raise EmptyLootPoolError(
                "Cannot loot: Valid item pool is empty."
            )

        data = random.choice(self.valid_items)
        return Item(
            data["name"],
            data["base_value"],
            data["base_condition"],
            category=data.get("category", "Unknown"),
            model_file=data.get("model")
        )