import asyncio
import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from openai import AsyncOpenAI, OpenAIError

from bot.config import Settings
from bot.database.models import Profile
from bot.services.prompts import (
    COMPATIBILITY_INSTRUCTIONS,
    COMPATIBILITY_PROMPT_VERSION,
    DAILY_FORECAST_INSTRUCTIONS,
    DAILY_FORECAST_PROMPT_VERSION,
    MONTHLY_FORECAST_INSTRUCTIONS,
    MONTHLY_FORECAST_PROMPT_VERSION,
    NATAL_CHART_INSTRUCTIONS,
    NATAL_CHART_PROMPT_VERSION,
    NUMEROLOGY_INSTRUCTIONS,
    NUMEROLOGY_PROMPT_VERSION,
    PERSONAL_QUESTION_INSTRUCTIONS,
    PERSONAL_QUESTION_PROMPT_VERSION,
    TAROT_INSTRUCTIONS,
    TAROT_PROMPT_VERSION,
    build_compatibility_input,
    build_daily_forecast_input,
    build_monthly_forecast_input,
    build_natal_chart_input,
    build_numerology_input,
    build_personal_question_input,
    build_tarot_input,
)
from bot.utils.zodiac import get_zodiac_element, get_zodiac_sign

logger = logging.getLogger(__name__)

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_MOJIBAKE_PATTERNS = (
    "Ð",
    "Ñ",
    "Â",
    "â€",
    "â€™",
    "â€œ",
    "â€",
    "â€¦",
    "â€”",
    "â€“",
    "âœ",
    "ðŸ",
)


class AIServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class AIResult:
    text: str
    provider: str
    model: str
    prompt_version: str
    is_demo: bool


class AstrobotAIService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate_daily_forecast(
        self,
        profile: Profile,
        current_date: date,
    ) -> AIResult:
        provider = self._get_provider()
        if provider == "demo":
            return AIResult(
                text=_build_demo_forecast(profile, current_date),
                provider="demo",
                model="local-template",
                prompt_version=DAILY_FORECAST_PROMPT_VERSION,
                is_demo=True,
            )
        result_text = await self._generate_openai(
            instructions=DAILY_FORECAST_INSTRUCTIONS,
            input_text=build_daily_forecast_input(profile, current_date),
        )
        return AIResult(
            text=result_text,
            provider="openai",
            model=self.settings.ai_model,
            prompt_version=DAILY_FORECAST_PROMPT_VERSION,
            is_demo=False,
        )

    async def generate_personal_question(
        self,
        profile: Profile,
        question_area: str,
        question_text: str,
        current_date: date,
    ) -> AIResult:
        provider = self._get_provider()
        if provider == "demo":
            return AIResult(
                text=_build_demo_question(profile, question_area, question_text),
                provider="demo",
                model="local-template",
                prompt_version=PERSONAL_QUESTION_PROMPT_VERSION,
                is_demo=True,
            )

        result_text = await self._generate_openai(
            instructions=PERSONAL_QUESTION_INSTRUCTIONS,
            input_text=build_personal_question_input(
                profile,
                question_area,
                question_text,
                current_date,
            ),
            max_output_tokens=max(self.settings.ai_max_output_tokens, 1400),
            max_chars=4500,
        )
        return AIResult(
            text=result_text,
            provider="openai",
            model=self.settings.ai_model,
            prompt_version=PERSONAL_QUESTION_PROMPT_VERSION,
            is_demo=False,
        )

    async def generate_compatibility(
        self,
        profile: Profile,
        relationship_type: str,
        partner_name: str,
        partner_birth_date: date | None,
        partner_birth_time: str | None,
        partner_birth_place: str | None,
        current_date: date,
    ) -> AIResult:
        provider = self._get_provider()
        if provider == "demo":
            return AIResult(
                text=_build_demo_compatibility(
                    profile,
                    relationship_type,
                    partner_name,
                    partner_birth_date,
                ),
                provider="demo",
                model="local-template",
                prompt_version=COMPATIBILITY_PROMPT_VERSION,
                is_demo=True,
            )

        result_text = await self._generate_openai(
            instructions=COMPATIBILITY_INSTRUCTIONS,
            input_text=build_compatibility_input(
                profile=profile,
                relationship_type=relationship_type,
                partner_name=partner_name,
                partner_birth_date=partner_birth_date,
                partner_birth_time=partner_birth_time,
                partner_birth_place=partner_birth_place,
                current_date=current_date,
            ),
            max_output_tokens=max(self.settings.ai_max_output_tokens, 1600),
            max_chars=5200,
        )
        return AIResult(
            text=result_text,
            provider="openai",
            model=self.settings.ai_model,
            prompt_version=COMPATIBILITY_PROMPT_VERSION,
            is_demo=False,
        )

    async def generate_monthly_forecast(
        self,
        profile: Profile,
        period: str,
        area: str,
        current_date: date,
    ) -> AIResult:
        provider = self._get_provider()
        if provider == "demo":
            return AIResult(
                text=_build_demo_monthly_forecast(profile, period, area),
                provider="demo",
                model="local-template",
                prompt_version=MONTHLY_FORECAST_PROMPT_VERSION,
                is_demo=True,
            )

        result_text = await self._generate_openai(
            instructions=MONTHLY_FORECAST_INSTRUCTIONS,
            input_text=build_monthly_forecast_input(
                profile,
                period,
                area,
                current_date,
            ),
            max_output_tokens=max(self.settings.ai_max_output_tokens, 1500),
            max_chars=5000,
        )
        return AIResult(
            text=result_text,
            provider="openai",
            model=self.settings.ai_model,
            prompt_version=MONTHLY_FORECAST_PROMPT_VERSION,
            is_demo=False,
        )

    async def generate_natal_chart(
        self,
        profile: Profile,
        focus: str,
        subfocus: str,
        life_stage: str,
        time_accuracy: str,
        time_period: str | None,
        current_date: date,
    ) -> AIResult:
        provider = self._get_provider()
        if provider == "demo":
            return AIResult(
                text=_build_demo_natal_chart(
                    profile,
                    focus,
                    subfocus,
                    life_stage,
                    time_accuracy,
                    time_period,
                ),
                provider="demo",
                model="local-template",
                prompt_version=NATAL_CHART_PROMPT_VERSION,
                is_demo=True,
            )
        result_text = await self._generate_openai(
            instructions=NATAL_CHART_INSTRUCTIONS,
            input_text=build_natal_chart_input(
                profile=profile,
                focus=focus,
                subfocus=subfocus,
                life_stage=life_stage,
                time_accuracy=time_accuracy,
                time_period=time_period,
                current_date=current_date,
            ),
            max_output_tokens=max(self.settings.ai_max_output_tokens, 2600),
            max_chars=9000,
        )
        return AIResult(
            text=result_text,
            provider="openai",
            model=self.settings.ai_model,
            prompt_version=NATAL_CHART_PROMPT_VERSION,
            is_demo=False,
        )

    async def generate_tarot_reading(
        self,
        profile: Profile,
        spread: str,
        area: str,
        question: str,
        cards: list[dict[str, str]],
        current_date: date,
    ) -> AIResult:
        provider = self._get_provider()
        if provider == "demo":
            return AIResult(
                text=_build_demo_tarot(profile, spread, area, question, cards),
                provider="demo",
                model="local-template",
                prompt_version=TAROT_PROMPT_VERSION,
                is_demo=True,
            )
        result_text = await self._generate_openai(
            instructions=TAROT_INSTRUCTIONS,
            input_text=build_tarot_input(
                profile=profile,
                spread=spread,
                area=area,
                question=question,
                cards=cards,
                current_date=current_date,
            ),
            max_output_tokens=max(self.settings.ai_max_output_tokens, 1400),
            max_chars=3800,
        )
        return AIResult(
            text=result_text,
            provider="openai",
            model=self.settings.ai_model,
            prompt_version=TAROT_PROMPT_VERSION,
            is_demo=False,
        )

    async def generate_numerology(
        self,
        profile: Profile,
        period: str,
        numbers: dict[str, int],
        current_date: date,
    ) -> AIResult:
        provider = self._get_provider()
        if provider == "demo":
            return AIResult(
                text=_build_demo_numerology(profile, period, numbers),
                provider="demo",
                model="local-template",
                prompt_version=NUMEROLOGY_PROMPT_VERSION,
                is_demo=True,
            )
        result_text = await self._generate_openai(
            instructions=NUMEROLOGY_INSTRUCTIONS,
            input_text=build_numerology_input(profile, period, numbers, current_date),
            max_output_tokens=max(self.settings.ai_max_output_tokens, 1400),
            max_chars=4500,
        )
        return AIResult(
            text=result_text,
            provider="openai",
            model=self.settings.ai_model,
            prompt_version=NUMEROLOGY_PROMPT_VERSION,
            is_demo=False,
        )

    def _get_provider(self) -> str:
        provider = self.settings.ai_provider.strip().lower()
        if provider not in {"demo", "openai"}:
            raise AIServiceError(f"Неизвестный AI-провайдер: {provider}")
        return provider

    async def _generate_openai(
        self,
        instructions: str,
        input_text: str,
        max_output_tokens: int | None = None,
        max_chars: int = 3400,
    ) -> str:
        api_key = (
            self.settings.ai_api_key.get_secret_value().strip()
            if self.settings.ai_api_key
            else ""
        )
        if not api_key:
            raise AIServiceError("Для OpenAI не настроен API-ключ")

        client = AsyncOpenAI(
            api_key=api_key,
            timeout=self.settings.ai_timeout_seconds,
        )
        try:
            for attempt in range(2):
                try:
                    response = await client.responses.create(
                        model=self.settings.ai_model,
                        instructions=instructions,
                        input=input_text,
                        max_output_tokens=(
                            max_output_tokens or self.settings.ai_max_output_tokens
                        ),
                    )
                    result_text = _clean_result(response.output_text, max_chars=max_chars)
                    if not result_text:
                        raise AIServiceError("AI вернул пустой ответ")
                    if _looks_like_mojibake(result_text):
                        raise AIServiceError(
                            "AI вернул текст с признаками повреждённой кодировки"
                        )
                    return result_text
                except (OpenAIError, AIServiceError) as error:
                    logger.warning(
                        "Ошибка OpenAI при генерации прогноза, попытка %s: %s",
                        attempt + 1,
                        type(error).__name__,
                    )
                    if attempt == 0:
                        await asyncio.sleep(1)
                        continue
                    if isinstance(error, AIServiceError):
                        raise error
                    raise AIServiceError("Не удалось получить ответ от AI-сервиса") from error
        finally:
            await client.close()

        raise AIServiceError("Не удалось создать прогноз")


def _clean_result(value: str | None, max_chars: int = 3400) -> str:
    text = unicodedata.normalize("NFC", value or "")
    text = _CONTROL_CHARS_RE.sub("", text)
    text = text.strip().replace("**", "").replace("__", "")
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", maxsplit=1)[0].rstrip() + "…"
    return text


def _looks_like_mojibake(value: str) -> bool:
    """Detect common UTF-8-as-Windows-1252 artifacts in Russian answers."""
    if not value:
        return False
    hits = sum(value.count(pattern) for pattern in _MOJIBAKE_PATTERNS)
    if hits >= 2:
        return True
    return bool(re.search(r"[ÐÑÂ]{2,}|â[€œ€™€¦–—]|ðŸ", value))


def _build_demo_forecast(profile: Profile, current_date: date) -> str:
    sign = get_zodiac_sign(profile.birth_date)
    seed = hashlib.sha256(
        f"{profile.birth_date.isoformat()}:{current_date.isoformat()}".encode()
    ).digest()[0]

    energy = [
        "Сегодня лучше двигаться спокойно и замечать детали: одна небольшая подсказка может заметно упростить день.",
        "День поддерживает ясные намерения. Выбери главное направление и не распыляй внимание на случайные задачи.",
        "Сегодня особенно полезно сверять решения со своим внутренним ощущением, не торопясь отвечать на внешнее давление.",
        "В первой половине дня наведи порядок в делах, а во второй оставь пространство для неожиданной полезной идеи.",
    ][seed % 4]
    relationships = [
        "В отношениях сработает простота: задай прямой вопрос и внимательно выслушай ответ, не додумывая за другого человека.",
        "Теплое проявление внимания окажется важнее длинных объяснений. Хороший день, чтобы спокойно обозначить свои чувства.",
        "Не спеши оценивать чужую реакцию. Небольшая пауза поможет увидеть мотивы собеседника мягче и точнее.",
        "Сегодня можно восстановить близость через обычный честный разговор без попытки немедленно решить все вопросы.",
    ][(seed + 1) % 4]
    work = [
        "В работе начни с задачи, которая давно отнимает внимание. Завершение одного дела освободит больше энергии, чем старт трех новых.",
        "Полезно проверить договоренности и сроки. Твоя сила сегодня в последовательности и ясной формулировке следующего шага.",
        "Не прячь хорошую идею, но сначала придай ей простую форму. Короткий план поможет получить поддержку окружающих.",
        "Делай ставку на качество, а не скорость. Спокойная проверка результата убережет от лишнего повторения работы.",
    ][(seed + 2) % 4]
    money = [
        "В денежных вопросах придерживайся заранее выбранного плана и отложи импульсивную покупку хотя бы на несколько часов.",
        "Сегодня полезно заметить мелкие регулярные расходы. Небольшая корректировка даст ощущение большего контроля.",
        "Не принимай финансовые решения под влиянием чужой спешки. Сначала собери факты и дай себе время подумать.",
        "Хороший день для наведения порядка в бюджете, но не для рискованных обещаний или необдуманных обязательств.",
    ][(seed + 3) % 4]
    advice = [
        "Запиши одно важное намерение на день и вечером отметь даже небольшой прогресс.",
        "Перед важным ответом сделай короткую паузу и три спокойных вдоха.",
        "Освободи десять минут от уведомлений и доведи до конца одну выбранную задачу.",
        "Спроси себя: какой самый бережный и реалистичный шаг доступен мне прямо сейчас?",
    ][(seed + 4) % 4]

    return f"""🔮 Твой прогноз на сегодня, {profile.name}

💫 Главная энергия дня
Для знака {sign} сегодня важны осознанный темп и внимание к собственным приоритетам. {energy}

💌 Любовь и эмоции
{relationships}

💼 Работа и дела
{work}

💰 Деньги
{money}

🧭 Совет дня
{advice}"""


def _build_demo_question(
    profile: Profile,
    question_area: str,
    question_text: str,
) -> str:
    return f"""💌 Ответ на твой вопрос, {profile.name}

📝 Как я понимаю ситуацию
Твой вопрос относится к сфере «{question_area}»: {question_text}

🔮 Короткий ответ
Сейчас полезнее не искать единственный заранее определенный исход, а посмотреть, какая часть ситуации действительно находится под твоим влиянием. Ясность может появиться через спокойный разговор, проверку предположений и небольшой следующий шаг.

💫 Что влияет на ситуацию
На восприятие могут одновременно влиять ожидания, прежний опыт и желание получить определенность как можно быстрее. Чем сильнее внутреннее напряжение, тем легче принять опасение за факт. Отдели то, что уже известно, от того, что пока только предполагается.

🪞 Чего можно не замечать
Возможно, ты предъявляешь к себе требование решить все сразу. Но ситуация может раскрываться постепенно, и пауза не обязательно означает отказ или неудачу. Иногда она дает возможность увидеть собственные границы и настоящие приоритеты.

🧭 Лучший следующий шаг
1. Запиши известные факты без оценок.
2. Сформулируй один прямой вопрос, который можно задать участникам ситуации.
3. Выбери действие, которое безопасно и выполнимо в ближайшие сутки.

⚠️ Чего лучше избегать
• решений на пике эмоций;
• попытки угадать чужие мысли;
• обещаний, которые тебе трудно выполнить.

✨ Итог
Твоя опора сейчас — не в точном предсказании, а в способности двигаться бережно, проверять реальность и сохранять право изменить решение, когда появятся новые факты."""


def _build_demo_compatibility(
    profile: Profile,
    relationship_type: str,
    partner_name: str,
    partner_birth_date: date | None,
) -> str:
    user_sign = get_zodiac_sign(profile.birth_date)
    user_element = get_zodiac_element(user_sign)
    if partner_birth_date is None:
        signs_context = (
            f"Дата рождения {partner_name} не указана, поэтому разбор опирается на "
            f"солнечный знак {user_sign}, тип отношений и общие закономерности общения."
        )
        dynamic = "Особенно полезно сверять выводы с реальным поведением, потребностями и договорённостями между вами."
    else:
        partner_sign = get_zodiac_sign(partner_birth_date)
        partner_element = get_zodiac_element(partner_sign)
        signs_context = f"Этот символический разбор сопоставляет солнечные знаки {user_sign} и {partner_sign}."
        if user_element == partner_element:
            dynamic = "Вам может быть проще узнавать в реакциях друг друга знакомый ритм, хотя похожие слабые места иногда усиливаются."
        elif {user_element, partner_element} in ({"Огонь", "Воздух"}, {"Земля", "Вода"}):
            dynamic = "Ваши стили могут естественно поддерживать друг друга: один приносит импульс, другой помогает ему обрести направление и форму."
        else:
            dynamic = "Ваши способы реагировать могут заметно различаться, и именно это способно стать как источником интереса, так и поводом учиться лучше понимать друг друга."

    return f"""🧩 Совместимость: {profile.name} и {partner_name}

💫 Общая динамика
{signs_context} Контекст отношений — «{relationship_type}». {dynamic} Связь лучше оценивать не по одному признаку, а по тому, насколько вы умеете слышать потребности и уважать границы друг друга.

💌 Эмоциональная связь
Один из вас может быстрее выражать переживания словами или действием, а другому может требоваться пауза. Это не обязательно означает холодность или отсутствие интереса. Полезно заранее обсуждать, какая поддержка действительно нужна каждому.

🗣️ Общение
Сильной стороной может стать любопытство к чужой точке зрения. Недоразумения вероятнее возникают, когда ожидания остаются невысказанными. Прямые вопросы, конкретные договоренности и отказ от чтения мыслей заметно укрепят контакт.

🔥 Притяжение и интерес
Различия способны поддерживать интерес, если не превращать их в соревнование. Похожесть, наоборот, дает ощущение узнавания, но требует пространства для индивидуальности.

⚡ Зоны напряжения
• разный темп принятия решений;
• ожидание, что другой сам догадается о потребностях;
• попытка доказать свою правоту вместо поиска общего решения.

🪞 Что важно понять тебе
Твоя задача не угадать будущее этой связи, а заметить, насколько свободно ты можешь говорить о важном и оставаться собой рядом с другим человеком.

🌙 Что может быть важно второму человеку
Второму человеку может быть важно чувствовать, что его стиль общения не оценивают заранее. Это лишь возможный сценарий — реальные потребности лучше уточнять в прямом разговоре.

🧭 Как мягче выстраивать контакт
1. Обсуждайте одну тему за раз.
2. Проверяйте предположения вопросами.
3. Формулируйте просьбы конкретно.
4. Оставляйте друг другу право на паузу.

✨ Итог
Совместимость не является приговором или гарантией. Это карта возможных различий и точек опоры, а качество связи создается вашими решениями, уважением и готовностью разговаривать."""


def _build_demo_monthly_forecast(
    profile: Profile,
    period: str,
    area: str,
) -> str:
    sign = get_zodiac_sign(profile.birth_date)
    return f"""🌙 Прогноз на {period} для {profile.name}

💫 Главная тема месяца
Для знака {sign} этот символический период предлагает соединить ясный план с вниманием к собственному состоянию. Главный фокус — «{area}». Не стремись получить все ответы в первые дни: полезная картина будет складываться постепенно.

🌒 Первая половина
Начало месяца подходит для ревизии незавершенных дел и договоренностей. Выбери две основные задачи и освободи им место в расписании. Там, где возникает спешка, сначала проверь факты и только затем отвечай.

🌘 Вторая половина
Во второй части месяца станет заметнее, какие решения действительно поддерживают твои приоритеты. Это хорошее время для спокойной корректировки курса, завершения лишних обязательств и закрепления полезного ритма.

💌 Любовь и отношения
Честность будет работать лучше намеков. Говори о своих потребностях конкретно, не приписывая другому человеку заранее известную реакцию. Теплые повседневные проявления внимания могут оказаться важнее больших обещаний.

💼 Работа и дела
Ставь качество выше количества. Один хорошо оформленный результат поможет больше, чем несколько начатых направлений. В обсуждениях фиксируй договоренности письменно и оставляй время на проверку деталей.

💰 Деньги
Полезно придерживаться заранее определенного бюджета и замечать небольшие повторяющиеся расходы. Не принимай финансовые решения под влиянием чужого давления или эмоционального импульса.

🧘 Внутреннее состояние
Поддерживай себя через предсказуемый режим, короткие паузы и уменьшение информационного шума. Усталость не требует немедленного жизненного решения — иногда сначала нужен обычный отдых.

⚠️ Чего лучше избегать
• обещаний из чувства вины;
• попытки решить все одновременно;
• поспешных выводов о мотивах других людей.

🧭 Лучшие действия месяца
1. Определи один измеримый приоритет.
2. Раз в неделю проверяй нагрузку и бюджет.
3. Проведи один честный разговор, который давно откладывался.

✨ Итог
Этот месяц не требует идеальности. Твоя опора — последовательные действия, ясные границы и готовность менять темп, когда реальность дает новую информацию."""


def _build_demo_natal_chart(
    profile: Profile,
    focus: str,
    subfocus: str,
    life_stage: str,
    time_accuracy: str,
    time_period: str | None,
) -> str:
    sign = get_zodiac_sign(profile.birth_date)
    time_note = (
        f"Время рождения указано как {profile.birth_time:%H:%M}."
        if profile.birth_time
        else "Точное время рождения неизвестно."
    )
    place_note = profile.birth_place or "место рождения не указано"
    period_note = f" Известное время суток: {time_period}." if time_period else ""
    return f"""🪐 Натальная карта для {profile.name}

✨ Важное уточнение
Это символический астропортрет по солнечному знаку {sign} и доступным данным рождения. {time_note} Точность времени: {time_accuracy}.{period_note} Место: {place_note}. Точные положения планет, дома, аспекты и Асцендент здесь не рассчитываются.

💫 Ядро личности
В твоем характере может сочетаться стремление сохранять собственный внутренний ритм с потребностью видеть смысл в происходящем. Для тебя особенно важно не просто выполнять задачи, а понимать, зачем они нужны и насколько согласуются с твоими ценностями. Сильнее всего ты раскрываешься там, где можешь действовать осознанно, а не только реагировать на ожидания окружающих.

🌙 Эмоциональная природа
Чувства могут становиться яснее не мгновенно, а после небольшой паузы. В напряженных ситуациях тебе полезно сначала вернуть ощущение опоры, затем называть переживание и только потом принимать решение. Безопасность укрепляют предсказуемые договоренности, уважение границ и право не давать немедленный ответ.

🔥 Сильные стороны
• способность замечать смысл и общую картину;
• верность важным для тебя людям и принципам;
• умение учиться на опыте;
• чувствительность к атмосфере общения;
• потенциал соединять интуицию с практическим шагом;
• способность поддерживать других без громких обещаний.

🪞 Теневые сценарии
Иногда высокая внутренняя планка может превращаться в сомнение: достаточно ли хорошо ты справляешься. Возможны попытки долго готовиться вместо начала, брать на себя чужое настроение или ждать полной уверенности перед простым действием. Это не неизменные черты, а сценарии, которые легче замечать и корректировать постепенно.

💌 Любовь и отношения
В близости тебе может быть важно сочетание тепла и свободы оставаться собой. Недосказанность способна вызывать больше напряжения, чем честный спокойный разговор. Полезно прямо обсуждать ожидания, способы поддержки и личное пространство, не пытаясь заранее угадать мысли другого человека.

💼 Работа и реализация
Тебе могут подходить роли, где есть понятная польза, пространство для самостоятельности и возможность развивать мастерство. Сложнее становится в среде постоянной хаотичной срочности или неясных правил. Главный фокус этого разбора — «{focus}», уточнение — «{subfocus}». Текущий жизненный этап: «{life_stage}». Ищи не идеальную роль, а условия, в которых твои сильные стороны проявляются регулярно.

💰 Деньги и ценность
Финансовая устойчивость поддерживается ясными бытовыми правилами, а не эмоциональными рывками. Полезно отделять желание порадовать себя от попытки снять напряжение покупкой и сверять крупные решения с заранее выбранным бюджетом. Это не инвестиционная рекомендация, а приглашение лучше замечать собственный денежный стиль.

🧭 Жизненное направление
Важной темой развития может быть переход от внешнего подтверждения к более устойчивой внутренней оценке. Чем яснее ты понимаешь свои приоритеты, тем проще выбирать проекты, отношения и обязательства без ощущения, что нужно соответствовать всем сразу.

🌱 Практические рекомендации
1. Запиши три условия, в которых ты работаешь и живешь лучше всего.
2. Раз в неделю проверяй, какие обязательства действительно остаются твоими.
3. В важном разговоре формулируй одну конкретную просьбу вместо намека.
4. Отделяй факты от предположений перед значимым решением.
5. Оставляй в расписании время без внешних требований.

✨ Итог
Эта карта — не рамка и не предсказание. Используй ее как набор вопросов и ориентиров, которые помогают внимательнее понимать свои реакции, силу и направление роста."""


def _build_demo_tarot(
    profile: Profile,
    spread: str,
    area: str,
    question: str,
    cards: list[dict[str, str]],
) -> str:
    sign = get_zodiac_sign(profile.birth_date)
    first, second, third = cards
    return f"""🃏 Таро + астрология: разбор ситуации

📝 Вопрос
{question}

Расклад «{spread}» относится к сфере «{area}». Карты выбраны случайно и используются как символы для размышления, а солнечный знак {sign} — как мягкий контекст.

🔮 Карта 1 — текущая ситуация
{first['card']} ({first['orientation']}). Образ этой карты предлагает посмотреть на то, что уже началось и требует осознанного участия. Сейчас полезно отделить реальные факты от ожиданий и выбрать ту часть ситуации, на которую ты действительно можешь влиять.

🌙 Карта 2 — скрытое влияние
{second['card']} ({second['orientation']}). Возможно, неочевидную роль играет прежний опыт или желание получить определенность слишком быстро. Карта не сообщает скрытые факты, а приглашает проверить собственные предположения.

🧭 Карта 3 — совет
{third['card']} ({third['orientation']}). Лучший ориентир — небольшой обратимый шаг: уточнить информацию, спокойно обозначить потребность или дать себе ограниченное время на решение.

⚡ Главный вызов
Не превращать тревогу в доказательство и не отдавать символическому раскладу ответственность за выбор. Решение остаётся за тобой и может меняться при появлении новых фактов.

⚠️ Чего лучше избегать
• резких решений на пике эмоций;
• попытки угадать чужие мысли;
• финансового или личного риска ради проверки предсказания.

✨ Итог
Карты не определяют будущее. Используй их как три разных угла зрения, которые помогают яснее сформулировать следующий безопасный шаг."""


def _build_demo_numerology(
    profile: Profile,
    period: str,
    numbers: dict[str, int],
) -> str:
    return f"""🔢 Нумерологический разбор для {profile.name}

Этот разбор относится к формату «{period}». Нумерология используется здесь как символический язык для саморефлексии, а не как научный прогноз.

💫 Число жизненного пути — {numbers['life_path']}
Это число можно воспринимать как образ долгосрочного способа учиться, выбирать направление и раскрывать сильные стороны. Полезнее искать не жесткое описание характера, а ситуации, в которых тебе легче проявлять инициативу, устойчивость и любопытство.

🎂 Число дня рождения — {numbers['birthday_number']}
Оно символически описывает естественный стиль действий. Обрати внимание, какие качества проявляются без внешнего давления и где они превращаются в перегрузку или завышенные требования к себе.

🌟 Личный год — {numbers['personal_year']}
Главной темой года может стать осознанный выбор приоритетов. Не обязательно менять всё сразу: достаточно регулярно сверять обязательства с тем, что действительно остаётся важным.

🌙 Личный месяц — {numbers['personal_month']}
Текущий месяц поддерживает конкретные небольшие шаги и завершение лишнего. Полезно уменьшить число параллельных задач и сохранить место для корректировки планов.

☀️ Личный день — {numbers['personal_day']}
Сегодняшний символический ориентир — соединять намерение с выполнимым действием. Перед важным ответом проверь факты и дай себе короткую паузу.

💌 Отношения
Прямой разговор работает лучше попытки угадать чужую реакцию. Говори о потребностях конкретно и оставляй другому человеку право на собственный темп.

💼 Работа и дела
Сосредоточься на результате, который можно завершить и показать. Нумерологический образ не заменяет факты, навыки и реальные условия выбора.

🧭 Лучшие действия
1. Определи один главный приоритет периода.
2. Заверши одно обязательство перед началом нового.
3. В конце недели оцени фактический прогресс без самокритики.

✨ Итог
Числа не назначают судьбу. Используй их как повод задать себе точные вопросы и выбрать следующий безопасный шаг."""
