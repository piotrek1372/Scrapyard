"""
Internationalization (i18n) module for Scrapyard.

Provides multi-language support with:
- 15 most widely used languages
- Automatic system language detection
- English fallback
- Translation of game strings, item names, and categories
"""

import locale
from src.utils.path_manager import PathManager

SUPPORTED_LANGUAGES = [
    "en",  # English (default / fallback)
    "zh",  # 中文 (Chinese)
    "hi",  # हिन्दी (Hindi)
    "es",  # Español (Spanish)
    "ar",  # العربية (Arabic)
    "bn",  # বাংলা (Bengali)
    "pt",  # Português (Portuguese)
    "ja",  # 日本語 (Japanese)
    "ko",  # 한국어 (Korean)
    "de",  # Deutsch (German)
    "fr",  # Français (French)
    "it",  # Italiano (Italian)
    "tr",  # Türkçe (Turkish)
    "ru",  # Русский (Russian)
    "pl",  # Polski (Polish)
]

DEFAULT_LANGUAGE = "en"


class I18n:
    """Singleton internationalization manager.

    Handles loading translations, detecting system language,
    and providing translated strings via key lookup.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._path_manager = PathManager()
        self._current_lang: str = DEFAULT_LANGUAGE
        self._translations: dict = {}
        self._fallback: dict = {}

        # Load English as fallback first
        self._fallback = self._path_manager.load_lang_file(DEFAULT_LANGUAGE)

        # Detect and apply system language
        detected = self._detect_system_language()
        self.set_language(detected)

    @staticmethod
    def _detect_system_language() -> str:
        """Detects the operating system's language setting.

        Uses locale.getdefaultlocale() to read the system language,
        extracts the 2-letter ISO 639-1 code, and validates it
        against SUPPORTED_LANGUAGES.

        Returns:
            str: 2-letter language code, or 'en' if unsupported/undetectable.
        """
        try:
            lang, _ = locale.getdefaultlocale()
            if lang:
                lang_code = lang[:2].lower()
                if lang_code in SUPPORTED_LANGUAGES:
                    return lang_code
        except (ValueError, TypeError):
            pass
        return DEFAULT_LANGUAGE

    def set_language(self, lang_code: str) -> None:
        """Sets the active language.

        Args:
            lang_code: 2-letter ISO 639-1 language code.
                       Falls back to 'en' if not supported.
        """
        if lang_code not in SUPPORTED_LANGUAGES:
            lang_code = DEFAULT_LANGUAGE

        self._current_lang = lang_code

        if lang_code == DEFAULT_LANGUAGE:
            self._translations = self._fallback
        else:
            loaded = self._path_manager.load_lang_file(lang_code)
            self._translations = loaded if loaded else self._fallback

    def get_language(self) -> str:
        """Returns the currently active language code."""
        return self._current_lang

    def get_supported_languages(self) -> list[str]:
        """Returns list of all supported language codes."""
        return list(SUPPORTED_LANGUAGES)

    def t(self, key: str, **kwargs) -> str:
        """Translates a dot-notation key with optional formatting.

        Traverses nested dicts using dot-separated keys.
        Falls back to English if key not found in current language.
        Falls back to the raw key if not found in English either.

        Args:
            key: Dot-notation key, e.g. 'game.overlooking'
            **kwargs: Format parameters, e.g. name='Rusty Radiator'

        Returns:
            str: Translated and formatted string.
        """
        result = self._resolve_key(key, self._translations)
        if result is None:
            result = self._resolve_key(key, self._fallback)
        if result is None:
            return key

        if kwargs:
            try:
                result = result.format(**kwargs)
            except (KeyError, IndexError):
                pass

        return self._apply_bidi(result)

    def t_item(self, english_name: str) -> str:
        """Translates an item name from its English base name.

        Args:
            english_name: The original English item name from items_db.json.

        Returns:
            str: Translated item name, or original English name if not found.
        """
        items = self._resolve_key("items", self._translations)
        if isinstance(items, dict) and english_name in items:
            return self._apply_bidi(items[english_name])

        items_fb = self._resolve_key("items", self._fallback)
        if isinstance(items_fb, dict) and english_name in items_fb:
            return self._apply_bidi(items_fb[english_name])

        return self._apply_bidi(english_name)

    def t_category(self, english_category: str) -> str:
        """Translates a category name from its English base name.

        Args:
            english_category: The original English category from items_db.json.

        Returns:
            str: Translated category name, or original if not found.
        """
        cats = self._resolve_key("categories", self._translations)
        if isinstance(cats, dict) and english_category in cats:
            return self._apply_bidi(cats[english_category])

        cats_fb = self._resolve_key("categories", self._fallback)
        if isinstance(cats_fb, dict) and english_category in cats_fb:
            return self._apply_bidi(cats_fb[english_category])

        return self._apply_bidi(english_category)

    @staticmethod
    def _resolve_key(key: str, data: dict):
        """Resolves a dot-notation key against a nested dict.

        Args:
            key: Dot-separated path, e.g. 'game.title'
            data: Nested dictionary to search.

        Returns:
            The value at the key path, or None if not found.
        """
        if not data:
            return None

        parts = key.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _apply_bidi(self, text: str) -> str:
        """Applies RTL layout and Arabic shaping if needed.

        Args:
            text: Original translated string.

        Returns:
            Properly shaped and reversed string for display.
        """
        if self._current_lang == "ar":
            try:
                import arabic_reshaper
                from bidi.algorithm import get_display
                return get_display(arabic_reshaper.reshape(text))
            except ImportError:
                pass
        return text


# ── Global convenience functions ──────────────────────────────────────────

def t(key: str, **kwargs) -> str:
    """Global shortcut for I18n().t() — translates a key."""
    return I18n().t(key, **kwargs)


def t_item(english_name: str) -> str:
    """Global shortcut for I18n().t_item() — translates an item name."""
    return I18n().t_item(english_name)


def t_category(english_category: str) -> str:
    """Global shortcut for I18n().t_category() — translates a category."""
    return I18n().t_category(english_category)
