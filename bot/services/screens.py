import logging

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import (
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

logger = logging.getLogger(__name__)

_last_screen_by_chat: dict[int, int] = {}


async def clear_screen(source: Message) -> None:
    chat_id = source.chat.id
    message_ids = {source.message_id}

    previous_message_id = _last_screen_by_chat.get(chat_id)
    if previous_message_id:
        message_ids.add(previous_message_id)

    for message_id in message_ids:
        try:
            await source.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except (TelegramBadRequest, TelegramForbiddenError):
            logger.debug(
                "Не удалось удалить сообщение %s в чате %s",
                message_id,
                chat_id,
            )


def remember_screen(message: Message) -> None:
    _last_screen_by_chat[message.chat.id] = message.message_id


async def show_screen(
    source: Message,
    text: str,
    reply_markup: (
        InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | None
    ) = None,
) -> Message:
    """Replace the previous bot screen with the current one."""
    await clear_screen(source)

    sent_message = await source.bot.send_message(
        chat_id=source.chat.id,
        text=text,
        reply_markup=reply_markup,
    )
    remember_screen(sent_message)
    return sent_message
