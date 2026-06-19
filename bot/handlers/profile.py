from datetime import date
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
    YEAR_PAGE_SIZE,
    birth_day_keyboard,
    birth_month_keyboard,
    birth_year_keyboard,
    initial_birth_year_page,
    place_input_keyboard,
    profile_actions_keyboard,
    profile_confirmation_keyboard,
    profile_delete_keyboard,
)
from bot.services.admin import notify_admin
from bot.services.screens import show_screen
from bot.states.profile import ProfileForm
from bot.texts.ru import (
    PROFILE_CONFIRM_PROMPT,
    PROFILE_DAY_PROMPT,
    PROFILE_DELETED_TEXT,
    PROFILE_DELETE_CONFIRM_TEXT,
    PROFILE_MONTH_PROMPT,
    PROFILE_NAME_PROMPT,
    PROFILE_PLACE_PROMPT,
    PROFILE_SAVED_TEXT,
    PROFILE_YEAR_PROMPT,
)
from bot.utils.profile import (
    normalize_birth_place,
    normalize_name,
)

router = Router(name="profile")


def format_profile_values(
    name: str,
    birth_date: date,
    birth_place: str | None,
) -> dict[str, str]:
    return {
        "name": escape(name),
        "birth_date": birth_date.strftime("%d.%m.%Y"),
        "birth_place": escape(birth_place) if birth_place else "Не указано",
    }


def profile_text(profile: Profile) -> str:
    values = format_profile_values(
        profile.name,
        profile.birth_date,
        profile.birth_place,
    )
    return (
        "👤 <b>Твой профиль</b>\n\n"
        f"Имя: {values['name']}\n"
        f"Дата рождения: {values['birth_date']}\n"
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


async def show_birth_year_picker(
    source: Message,
    state: FSMContext,
    page_start: int | None = None,
) -> None:
    data = await state.get_data()
    start_year = page_start if page_start is not None else initial_birth_year_page()
    minimum_year = date.today().year - 120
    start_year = max(minimum_year, min(start_year, date.today().year))
    end_year = min(start_year + YEAR_PAGE_SIZE - 1, date.today().year)
    await state.set_state(ProfileForm.birth_year)
    await show_screen(
        source,
        PROFILE_YEAR_PROMPT.format(
            name=escape(str(data.get("name", ""))),
            start_year=start_year,
            end_year=end_year,
        ),
        reply_markup=birth_year_keyboard(start_year),
    )


async def show_confirmation(source: Message, state: FSMContext) -> None:
    data = await state.get_data()
    values = format_profile_values(
        data["name"],
        data["birth_date"],
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
        ProfileForm.birth_year,
        ProfileForm.birth_month,
        ProfileForm.birth_day,
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


@router.callback_query(F.data == "profile:cancel")
async def cancel_profile_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
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
    await show_birth_year_picker(message, state)


@router.callback_query(ProfileForm.birth_year, F.data.startswith("profile:years:"))
async def change_birth_year_page(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    try:
        page_start = int((callback.data or "").rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return
    if isinstance(callback.message, Message):
        await show_birth_year_picker(callback.message, state, page_start)


@router.callback_query(ProfileForm.birth_year, F.data.startswith("profile:year:"))
async def select_birth_year(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    try:
        year = int((callback.data or "").rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return
    current_year = date.today().year
    if not current_year - 120 <= year <= current_year:
        return
    await state.update_data(birth_year=year)
    await state.set_state(ProfileForm.birth_month)
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            PROFILE_MONTH_PROMPT.format(year=year),
            reply_markup=birth_month_keyboard(year),
        )


@router.callback_query(ProfileForm.birth_month, F.data == "profile:year_back")
async def birth_year_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_birth_year_picker(callback.message, state)


@router.callback_query(ProfileForm.birth_month, F.data.startswith("profile:month:"))
async def select_birth_month(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    try:
        month = int((callback.data or "").rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return
    data = await state.get_data()
    year = int(data["birth_year"])
    if not 1 <= month <= 12:
        return
    if year == date.today().year and month > date.today().month:
        return
    await state.update_data(birth_month=month)
    await state.set_state(ProfileForm.birth_day)
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            PROFILE_DAY_PROMPT.format(year=year, month=month),
            reply_markup=birth_day_keyboard(year, month),
        )


@router.callback_query(ProfileForm.birth_day, F.data == "profile:month_back")
async def birth_month_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    year = int(data["birth_year"])
    await state.set_state(ProfileForm.birth_month)
    if isinstance(callback.message, Message):
        await show_screen(
            callback.message,
            PROFILE_MONTH_PROMPT.format(year=year),
            reply_markup=birth_month_keyboard(year),
        )


@router.callback_query(ProfileForm.birth_day, F.data.startswith("profile:day:"))
async def select_birth_day(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    try:
        day = int((callback.data or "").rsplit(":", 1)[1])
        data = await state.get_data()
        birth_date = date(int(data["birth_year"]), int(data["birth_month"]), day)
    except (IndexError, KeyError, TypeError, ValueError):
        return
    if birth_date > date.today():
        return
    await state.update_data(birth_date=birth_date)
    if isinstance(callback.message, Message):
        await ask_birth_place(callback.message, state)


@router.message(
    StateFilter(
        ProfileForm.birth_year,
        ProfileForm.birth_month,
        ProfileForm.birth_day,
    )
)
async def repeat_birth_date_buttons(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    data = await state.get_data()
    if current_state == ProfileForm.birth_month.state:
        year = int(data["birth_year"])
        await show_screen(
            message,
            "⚠️ Выбери месяц кнопкой.\n\n" + PROFILE_MONTH_PROMPT.format(year=year),
            reply_markup=birth_month_keyboard(year),
        )
    elif current_state == ProfileForm.birth_day.state:
        year = int(data["birth_year"])
        month = int(data["birth_month"])
        await show_screen(
            message,
            "⚠️ Выбери день кнопкой.\n\n" + PROFILE_DAY_PROMPT.format(year=year, month=month),
            reply_markup=birth_day_keyboard(year, month),
        )
    else:
        await show_birth_year_picker(message, state)


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
        birth_time=None,
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
    PROFILE_MONTH_PROMPT,
