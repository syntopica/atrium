"""A term-frequency vector over one block's human text."""

from collections import Counter

from atrium.synthesize.episode_word import EPISODE_WORD
from atrium.synthesize.stopwords import SPANISH_ENGLISH_STOPWORDS


def tf_vector(text: str) -> Counter[str]:
    """Count the lower-cased non-stopword words of ``text``."""
    words = [
        word.lower()
        for word in EPISODE_WORD.findall(text)
        if word.lower() not in SPANISH_ENGLISH_STOPWORDS
    ]
    return Counter(words)
