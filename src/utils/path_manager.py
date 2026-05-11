import json
from pathlib import Path
from typing import Any, Dict, List

class PathManager:
    """Manages paths and file loading for the Scrapyard game."""

    def __init__(self) -> None:
        """Initializes base paths constants using pathlib."""
        self.BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
        self.DATA_DIR: Path = self.BASE_DIR / "data"
        self.SAVES_DIR: Path = self.DATA_DIR / "saves"
        self.ASSETS_DIR: Path = self.BASE_DIR / "assets"
        self.MODELS_DIR: Path = self.ASSETS_DIR / "models"
        self.LANG_DIR: Path = self.DATA_DIR / "lang"

    def load_items_db(self, filename: str = "items_db.json") -> Any:
        """Loads json data from DATA_DIR by filename."""
        fullpath = self.DATA_DIR / filename
        with fullpath.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def load_lang_file(self, lang_code: str) -> Dict[str, Any]:
        """Loads translation JSON file for given language code.
        
        Returns empty dict if file not found.
        """
        fullpath = self.LANG_DIR / f"{lang_code}.json"
        if not fullpath.exists():
            return {}
        with fullpath.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def get_model_path(self, model_filename: str) -> Path:
        """Returns the full path to a model file."""
        return self.MODELS_DIR / model_filename

    def get_all_lang_files(self) -> List[Path]:
        """Returns a list of all language JSON files in LANG_DIR."""
        if not self.LANG_DIR.exists():
            return []
        return list(self.LANG_DIR.glob("*.json"))
