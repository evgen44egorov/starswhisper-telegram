CRISIS_PHRASES = (
    "хочу умереть",
    "не хочу жить",
    "покончить с собой",
    "покончу с собой",
    "убить себя",
    "совершить суицид",
    "планирую суицид",
)


def is_crisis_question(value: str) -> bool:
    normalized = " ".join(value.casefold().split())
    return any(phrase in normalized for phrase in CRISIS_PHRASES)

