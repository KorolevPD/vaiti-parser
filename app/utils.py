import re

SIMILAR_MAP = str.maketrans(
    {
        "A": "А",
        "B": "В",
        "C": "С",
        "E": "Е",
        "H": "Н",
        "K": "К",
        "M": "М",
        "O": "О",
        "P": "Р",
        "T": "Т",
        "X": "Х",
    }
)


def normalize(text: str) -> str:
    text = text.upper().translate(SIMILAR_MAP)
    return re.sub(r"[^A-ZА-Я0-9]", "", text)


def match(title: str, whitelist: list[str], blacklist: list[str]) -> bool:
    title = normalize(title)

    if whitelist and not any(normalize(w) in title for w in whitelist):
        return False

    if any(normalize(b) in title for b in blacklist):
        return False

    return True
