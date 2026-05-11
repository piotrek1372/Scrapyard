from random import randint
from os import path

class Item:
    def __init__(self, name: str, value: int, condition: float,
                 category: str = "Unknown", model_file: str = None) -> None:
        """Initializes Item class which represents single part"""
        self.name: str = name
        self.value: int = value + randint(-10, 10)
        self.condition: float = round(max(0.1, condition - randint(1, 10)/100), 2)
        self.category: str = category
        self.safe_name = name.lower().replace(" ", "-")

        # Build model path — points to specific .glb file or None
        base_dir = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))
        models_dir = path.join(base_dir, "assets", "models")
        if model_file:
            full_path = path.join(models_dir, model_file)
            self.model_path = full_path if path.exists(full_path) else None
        else:
            self.model_path = None

    def has_model(self) -> bool:
        """Returns True if this item has a .glb model file available."""
        return self.model_path is not None

    def __repr__(self) -> str:
        return f"Item({self.name}, Val: {self.value}, Cond: {self.condition})"