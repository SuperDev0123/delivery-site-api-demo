import re
from difflib import SequenceMatcher


def similarity(a, b):
    """
    get similarity between two chars
    """
    return SequenceMatcher(None, a, b).ratio()


def ireplace(old, repl, text):
    return re.sub("(?i)" + re.escape(old), lambda m: repl, text)


def toAlphaNumeric(text, replacement="_"):
    return re.sub(r"[^0-9a-zA-Z]+", replacement, text)
