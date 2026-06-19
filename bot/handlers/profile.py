from datetime import date, time
from html import escape

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot.database.models import Profile
from bot.database.repositories import delete_profile, get_profile, save_profile
from bot.keyboards.main_menu import PROFILE_BUTTON, main_menu_keyboard
from bot.keyboards.profile import (
    CANCEL_BUTTON,
    CONFIRM_PROFILE_BUTTON,
    RESTART_PROFILE_BUTTON,
    SKIP_PLACE_BUTTON,
    UNKNOWN_TIME_BUTTON,
    place_input_keyboard,
    profile_actions_keyboard,
    profile_confirmation_keyboard,
    profile_delete_keyboard,
    time_input_keyboard,
)
from bot.services.admin import notify_admin
from bot.services.screens import show_screen
from bot.states.profile import ProfileForm
from bot.texts.ru import (
    PROFILE_CONFIRM_PROMPT,
    PROFILE_DATE_PROMPT,
    PROFILE_DELETED_TEXT,
    PROFILE_DELETE_CONFIRM_TEXT,
    PROFILE_NAME_PROMPT,
    PROFILE_PLACE_PROMPT,
    PROFILE_SAVED_TEXT,
    PROFILE_TIME_PROMPT,
)
from bot.utils.profile import (
    normalize_birth_place,
    normalize_name,
    parse_birth_date,
    parse_birth_time,
)

router = Router(name="profile")


def format_profile_values(
    name: str,
    birth_date: date,
    birth_time: time | None,
    birth_place: str | None,
) -> dict[str, str]:
    return {
        "name": escape(name),
        "birth_date": birth_date.strftime("%d.%m.%Y"),
        "birth_time": birth_time.strftime("%H:%M") if birth_time else "Не указано",
        "birth_place": escape(birth_place) if birth_place else "Не указано",
    }


def profile_text(profile: Profile) -> str:
    values = format_profile_values(
        profile.name,
        profile.birth_date,
        profile.birth_time,
        profile.birth_place,
    )
    return (
        "👤 <b>Твой профиль</b>\n\n"
        f"Имя: {values['name']}\n"
        f"Дата рождения: {values['birth_date']}\n"
        f"Время рождения: {values['birth_time']}\n"
        f"Место рождения: {values['birth_place']}"
    )


async def begin_profile(source: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ProfileForm.name)
    await show_screen(source, PROFILE_NAME_PROMPT, reply_markup=ReplyKeyboardRemove())


async def display_profile(source: Message, telegram_id: int) -> None:
    profile = await get_profile(telegram_id)
    if profile is None:
        await show_screen(
            source,
            "👤 Профиль пока не заполнен.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await show_screen(
        source,
        profile_text(profile),
        reply_markup=profile_actions_keyboard(),
    )


async def ask_birth_place(source: Message, state: FSMContext) -> None:
    await state.set_state(ProfileForm.birth_place)
    await show_screen(
        source,
        PROFILE_PLACE_PROMPT,
        reply_markup=place_input_keyboard(),
    )


async def show_confirmation(source: Message, state: FSMContext) -> None:
    data = await state.get_data()
    values = format_profile_values(
        data["name"],
        data["birth_date"],
        data.get("birth_time"),
        data.get("birth_place"),
    )
    await state.set_state(ProfileForm.confirm)
    await show_screen(
        source,
        PROFILE_CONFIRM_PROMPT.format(**values),
        reply_markup=profile_confirmation_keyboard(),
    )


@router.callback_query(F.data == "start:profile")
async def start_profile_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await begin_profile(callback.message, state)


@router.message(F.text == PROFILE_BUTTON)
async def profile_menu(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    await state.clear()
    profile = await get_profile(message.from_user.id)
    if profile is None:
        await begin_profile(message, state)
        return

    await show_screen(
        message,
        profile_text(profile),
        reply_markup=profile_actions_keyboard(),
    )


@router.callback_query(F.data == "profile:edit")
async def edit_profile_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await begin_profile(callback.message, state)


@router.callback_query(F.data == "profile:delete")
async def delete_profile_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            PROFILE_DELETE_CONFIRM_TEXT,
            reply_markup=profile_delete_keyboard(),
        )


@router.callback_query(F.data == "profile:delete_confirm")
async def confirm_delete_profile_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    if callback.from_user:
        await delete_profile(callback.from_user.id)
    await state.clear()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            PROFILE_DELETED_TEXT,
            reply_markup=main_menu_keyboard(),
        )


@router.callback_query(F.data == "profile:delete_cancel")
async def cancel_delete_profile_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await display_profile(callback.message, callback.from_user.id)


@router.message(
    StateFilter(
        ProfileForm.name,
        ProfileForm.birth_date,
        ProfileForm.birth_time,
        ProfileForm.birth_place,
        ProfileForm.confirm,
    ),
    F.text == CANCEL_BUTTON,
)
async def cancel_profile(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_screen(
        message,
        "↩️ Заполнение профиля отменено.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(ProfileForm.name)
async def receive_name(message: Message, state: FSMContext) -> None:
    try:
        name = normalize_name(message.text or "")
    except ValueError as error:
        await show_screen(
            message,
            f"⚠️ {escape(str(error))}\n\n{PROFILE_NAME_PROMPT}",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(name=name)
    await state.set_state(ProfileForm.birth_date)
    await show_screen(
        message,
        PROFILE_DATE_PROMPT.format(name=escape(name)),
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(ProfileForm.birth_date)
async def receive_birth_date(message: Message, state: FSMContext) -> None:
    try:
        birth_date = parse_birth_date(message.text or "")
    except ValueError as error:
        await show_screen(
            message,
            f"⚠️ {escape(str(error))}\n\nУкажи дату в формате <b>ДД.ММ.ГГГГ</b>.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(birth_date=birth_date)
    await state.set_state(ProfileForm.birth_time)
    await show_screen(
        message,
        PROFILE_TIME_PROMPT,
        reply_markup=time_input_keyboard(),
    )


@router.message(ProfileForm.birth_time, F.text == UNKNOWN_TIME_BUTTON)
async def skip_birth_time(message: Message, state: FSMContext) -> None:
    await state.update_data(birth_time=None)
    await ask_birth_place(message, state)


@router.message(ProfileForm.birth_time)
async def receive_birth_time(message: Message, state: FSMContext) -> None:
    try:
        birth_time = parse_birth_time(message.text or "")
    except ValueError as error:
        await show_screen(
            message,
            f"⚠️ {escape(str(error))}\n\n{PROFILE_TIME_PROMPT}",
            reply_markup=time_input_keyboard(),
        )
        return

    await state.update_data(birth_time=birth_time)
    await ask_birth_place(message, state)


@router.message(ProfileForm.birth_place, F.text == SKIP_PLACE_BUTTON)
async def skip_birth_place(message: Message, state: FSMContext) -> None:
    await state.update_data(birth_place=None)
    await show_confirmation(message, state)


@router.message(ProfileForm.birth_place)
async def receive_birth_place(message: Message, state: FSMContext) -> None:
    try:
        birth_place = normalize_birth_place(message.text or "")
    except ValueError as error:
        await show_screen(
            message,
            f"⚠️ {escape(str(error))}\n\n{PROFILE_PLACE_PROMPT}",
            reply_markup=place_input_keyboard(),
        )
        return

    await state.update_data(birth_place=birth_place)
    await show_confirmation(message, state)


@router.message(ProfileForm.confirm, F.text == RESTART_PROFILE_BUTTON)
async def restart_profile(message: Message, state: FSMContext) -> None:
    await begin_profile(message, state)


@router.message(ProfileForm.confirm, F.text == CONFIRM_PROFILE_BUTTON)
async def confirm_profile(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    data = await state.get_data()
    is_new_user = await get_profile(message.from_user.id) is None
    profile = await save_profile(
        telegram_user=message.from_user,
        name=data["name"],
        birth_date=data["birth_date"],
        birth_time=data.get("birth_time"),
        birth_place=data.get("birth_place"),
    )
    if is_new_user:
        await notify_admin(
            message.bot,
            "👤 <b>Новый пользователь</b>\n\n"
            f"Telegram ID: <code>{message.from_user.id}</code>\n"
            f"Имя профиля: {escape(profile.name)}",
        )
    await state.clear()
    await show_screen(
        message,
        f"{PROFILE_SAVED_TEXT}\n\n{profile_text(profile)}",
        reply_markup=main_menu_keyboard(),
    )


@router.message(ProfileForm.confirm)
async def repeat_profile_confirmation(message: Message, state: FSMContext) -> None:
    await show_confirmation(message, state)
