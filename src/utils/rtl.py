"""
rtl.py — Right-to-left text preparation utilities.

Provides ``prepare_rtl(text)`` which applies:
  1. Arabic reshaping (contextual letter forms: initial, medial, final,
     isolated) via the ``arabic-reshaper`` library.
  2. Unicode Bidirectional Algorithm reordering via ``python-bidi``.

Both steps are required for correct Arabic rendering in game engines
(including Panda3D) that do not natively support BiDi or Arabic shaping.

Graceful fallback: if either library is not installed, the original text
is returned unchanged and a warning is logged once.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("Scrapyard.RTL")

# ── Library import with graceful fallback ─────────────────────────────────

_HAS_RESHAPER: bool = False
_HAS_BIDI: bool = False

try:
    import arabic_reshaper as _ar
    _HAS_RESHAPER = True
except ImportError:
    logger.warning(
        "arabic-reshaper not installed — Arabic text will not be shaped. "
        "Run: pip install arabic-reshaper"
    )

try:
    from bidi.algorithm import get_display as _get_display
    _HAS_BIDI = True
except ImportError:
    logger.warning(
        "python-bidi not installed — Arabic text will not be reordered RTL. "
        "Run: pip install python-bidi==0.4.2"
    )


def prepare_rtl(text: str) -> str:
    """Reshapes and reorders Arabic text for left-to-right renderers.

    Applies two transformations required for correct Arabic display:
    1. **Reshaping**: converts Unicode code points to their contextual
       glyph forms (how letters look when adjacent to other letters).
    2. **BiDi reordering**: reverses the logical order to visual order
       so a LTR renderer displays the text right-to-left correctly.

    If either library is unavailable, returns the original string unchanged.

    Args:
        text: Arabic (or mixed) text in logical Unicode order.

    Returns:
        Visually reordered text ready for rendering in a LTR text engine.

    Example:
        >>> prepare_rtl("العربية")
        'ﺔﻴﺑﺮﻌﻟا'   # shaped + reversed for LTR display
    """
    if not _HAS_RESHAPER and not _HAS_BIDI:
        return text

    result = text
    if _HAS_RESHAPER:
        result = _ar.reshape(result)
    if _HAS_BIDI:
        result = _get_display(result)
    return result
