# app/language_flags.py

LANGUAGE_FLAGS = {
    "en": "🇬🇧",  # English (UK)
    "es": "🇪🇸",  # Spanish
    "fr": "🇫🇷",  # French
    "de": "🇩🇪",  # German
    "it": "🇮🇹",  # Italian
    "pt": "🇧🇷",  # Portuguese
    "zh": "🇨🇳",  # Chinese
    "ja": "🇯🇵",  # Japanese
    "ko": "🇰🇷",  # Korean
    "ru": "🇷🇺",  # Russian
    "ro": "🇷🇴",  # Romanian
    "sq": "🇦🇱",  # Albanian
}

DEFAULT_FLAG = "🏳️"

def get_flag(language_code: str) -> str:
    if not language_code:
        return DEFAULT_FLAG
    return LANGUAGE_FLAGS.get(language_code.lower(), DEFAULT_FLAG)