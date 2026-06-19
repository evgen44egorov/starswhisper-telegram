import re
from html import escape

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup

from bot.database.models import Order
from bot.services.orders import service_label


def split_result_text(value: str, limit: int = 3400) -> list[str]:
    """Escape and split a long AI result without breaking HTML entities."""
    pieces = re.split(r"(\n\n+)", value.strip())
    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            chunks.append(escape(current.strip()))
        current = ""

    for piece in pieces:
        if not piece:
            continue
        candidate = current + piece
        if len(escape(candidate)) <= limit:
            current = candidate
            continue
        flush()
        if len(escape(piece)) <= limit:
            current = piece
            continue

        words = piece.split()
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(escape(candidate)) <= limit:
                current = candidate
            else:
                flush()
                if len(escape(word)) <= limit:
                    current = word
                else:
                    for start in range(0, len(word), limit // 2):
                        segment = word[start : start + limit // 2]
                        if len(escape(segment)) > limit:
                            segment = segment[: limit // 4]
                        chunks.append(escape(segment))
    flush()
    return chunks or [""]


def format_order_result_chunks(
    order: Order,
    result_text: str,
    is_demo: bool = False,
) -> list[str]:
    chunks = split_result_text(result_text)
    footer = (
        ("\n\n<i>🧪 Результат создан демонстрационным генератором.</i>" if is_demo else "")
        + f"\n\n<i>{service_label(order.service_code)} · заказ {escape(order.public_id)}</i>"
    )
    if len(chunks[-1]) + len(footer) <= 4000:
        chunks[-1] += footer
    else:
        chunks.append(footer.lstrip())
    if len(chunks) > 1:
        total = len(chunks)
        chunks = [f"<i>Часть {index}/{total}</i>\n\n{chunk}" for index, chunk in enumerate(chunks, 1)]
    return chunks


async def send_order_result(
    bot: Bot,
    chat_id: int,
    order: Order,
    result_text: str,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | None = None,
    is_demo: bool = False,
) -> Message:
    messages: list[Message] = []
    chunks = format_order_result_chunks(order, result_text, is_demo=is_demo)
    for index, chunk in enumerate(chunks):
        messages.append(
            await bot.send_message(
                chat_id=chat_id,
                text=chunk,
                reply_markup=reply_markup if index == len(chunks) - 1 else None,
            )
        )
    return messages[-1]
