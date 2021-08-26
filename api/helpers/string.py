from difflib import SequenceMatcher


def similarity(a, b):
    """
    get similarity between two chars
    """
    return SequenceMatcher(None, a, b).ratio()
