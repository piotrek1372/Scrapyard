import arabic_reshaper
from bidi.algorithm import get_display

text = 'اللغة: {lang}'
print("Original:", repr(text))
bidi_text = get_display(arabic_reshaper.reshape(text))
print("Bidi:", repr(bidi_text))

# Let's see what happens if we format it
try:
    print("Formatted:", repr(bidi_text.format(lang="ar")))
except Exception as e:
    print("Format error:", e)

# What if we format first, then bidi?
formatted = text.format(lang="ar")
print("Format first:", repr(get_display(arabic_reshaper.reshape(formatted))))
