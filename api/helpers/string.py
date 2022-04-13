from difflib import SequenceMatcher


def similarity(a, b):
    """
    get similarity between two chars
    """
    return SequenceMatcher(None, a, b).ratio()


def ireplace(old, repl, text):
    return re.sub("(?i)" + re.escape(old), lambda m: repl, text)
