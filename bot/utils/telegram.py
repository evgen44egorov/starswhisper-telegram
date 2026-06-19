from html import escape


def escape_and_limit(value: str, limit: int = 3400) -> str:
    escaped = escape(value.strip())
    if len(escaped) <= limit:
        return escaped

    shortened = escaped[:limit]
    if shortened.rfind("&") > shortened.rfind(";"):
        shortened = shortened[: shortened.rfind("&")]
    if " " in shortened:
        shortened = shortened.rsplit(" ", maxsplit=1)[0]
    return shortened.rstrip() + "…"

