import logging
from typing import Any, Dict, List

from src.utils.path_manager import PathManager

logger = logging.getLogger(__name__)


class ItemValidator:
    """Validates game items to ensure they are 100% ready for gameplay.
    
    Checks if 3D models exist and if all required translations are present.
    """

    def __init__(self) -> None:
        """Initializes ItemValidator and caches language files."""
        self._path_mgr = PathManager()
        self._lang_data: List[Dict[str, Any]] = self._load_all_languages()

    def _load_all_languages(self) -> List[Dict[str, Any]]:
        """Loads and caches all available language files."""
        lang_files = self._path_mgr.get_all_lang_files()
        loaded_langs = []
        for file_path in lang_files:
            lang_code = file_path.stem
            data = self._path_mgr.load_lang_file(lang_code)
            if data:
                loaded_langs.append(data)
        return loaded_langs

    def get_valid_items(self, items_db: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filters a list of items, returning only fully valid ones.
        
        An item is valid if:
        1. It has a 'model' key and the corresponding .glb file exists.
        2. Its 'name' key exists in the 'items' dict of all language files.
        """
        valid_items: List[Dict[str, Any]] = []

        for item in items_db:
            name = item.get("name", "Unknown")
            model = item.get("model")

            if not self._validate_model(name, model):
                continue
            
            if not self._validate_translations(name):
                continue

            valid_items.append(item)

        return valid_items

    def _validate_model(self, name: str, model: str | None) -> bool:
        """Validates if item has a model and if the file exists."""
        if not model:
            logger.warning(f"Item '{name}' rejected: No model specified.")
            return False
            
        model_path = self._path_mgr.get_model_path(model)
        if not model_path.exists():
            logger.warning(
                f"Item '{name}' rejected: Model file '{model}' not found."
            )
            return False
            
        return True

    def _validate_translations(self, name: str) -> bool:
        """Validates if the item name has translations in all loaded languages."""
        for lang in self._lang_data:
            items_dict = lang.get("items", {})
            if name not in items_dict:
                lang_name = lang.get("game", {}).get("title", "UnknownLang")
                # Using id() to distinguish if no clear name available,
                # but let's just say 'a language file'
                logger.warning(
                    f"Item '{name}' rejected: Missing translation in a "
                    f"language file."
                )
                return False
        return True
