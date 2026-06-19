# Astrobot Telegram: техническое задание MVP

Дата фиксации: 17 июня 2026.

## Цель MVP

Сделать первую рабочую версию Telegram-бота, который:

1. Показывает пользователю меню услуг.
2. Собирает данные для персонального разбора.
3. Принимает оплату через Telegram Stars.
4. Генерирует AI-ответ по выбранной услуге.
5. Отправляет результат пользователю в Telegram.
6. Сохраняет пользователя, заказ, платеж и результат в базе.
7. Уведомляет администратора о важных событиях.

## Что входит в первую версию

MVP-услуги:

1. Бесплатный дневной прогноз.
2. Расширенный прогноз на день за Stars.
3. Личный вопрос.
4. Совместимость.
5. Натальная карта.
6. Прогноз на месяц.

Будущие услуги, которые пока закладываем в архитектуру, но не обязаны запускать в первой версии:

1. Нумерология.
2. Таро + астрология.
3. Лунный календарь.
4. Подписки.
5. PDF-отчеты.
6. Внешний сайт.
7. Админ-панель в браузере.

## Рекомендуемый стек

### Язык и фреймворк

- Python 3.12+
- aiogram 3.x для Telegram-бота

### База данных

Для MVP:

- SQLite
- SQLAlchemy 2.x
- Alembic для миграций, если проект сразу делаем аккуратно

Для будущего продакшена:

- PostgreSQL

### AI-генерация

- Отдельный сервисный слой `ai_service`
- Конкретный провайдер AI должен задаваться через настройки
- Модель должна задаваться через переменную окружения, чтобы ее можно было менять без переписывания кода

### Хранение настроек

- `.env`
- Pydantic Settings или простой конфигурационный модуль

### Запуск

Для MVP:

- long polling

Для продакшена позже:

- webhook
- VPS или cloud hosting
- systemd/Docker

## Почему long polling для MVP

На старте long polling проще:

- не нужен домен;
- не нужен SSL;
- быстрее тестировать;
- меньше инфраструктуры.

Webhook включаем позже, когда бот стабильно работает и готов к публичному трафику.

## Архитектура приложения

Бот делится на несколько слоев:

1. Telegram-слой
   - команды;
   - кнопки;
   - обработчики сообщений;
   - обработчики оплат.

2. Сценарный слой
   - состояние пользователя;
   - сбор данных;
   - переходы между шагами;
   - выбор услуги.

3. Бизнес-слой
   - создание заказа;
   - расчет цены;
   - проверка оплаты;
   - запуск генерации;
   - выдача результата.

4. AI-слой
   - подготовка промпта;
   - вызов AI-модели;
   - проверка ответа;
   - сохранение результата.

5. Слой базы данных
   - пользователи;
   - профили;
   - заказы;
   - платежи;
   - результаты;
   - поддержка;
   - логи событий.

6. Админ-слой
   - уведомления администратору;
   - ручная проверка ошибок;
   - команды для просмотра заказов.

## Предлагаемая структура проекта

```text
astrobot/
  bot/
    __init__.py
    main.py
    config.py
    keyboards/
      main_menu.py
      services.py
      payments.py
    handlers/
      start.py
      menu.py
      profile.py
      forecast.py
      question.py
      compatibility.py
      natal_chart.py
      payments.py
      support.py
      admin.py
    states/
      profile.py
      orders.py
    services/
      orders.py
      payments.py
      ai.py
      prompts.py
      notifications.py
      safety.py
    database/
      models.py
      session.py
      repositories.py
      migrations/
    texts/
      ru.py
    utils/
      dates.py
      formatting.py
      validators.py
  tests/
  .env.example
  requirements.txt
  README.md
```

## Переменные окружения

```text
BOT_TOKEN=
ADMIN_TELEGRAM_ID=

DATABASE_URL=sqlite+aiosqlite:///./astrobot.db

AI_PROVIDER=
AI_API_KEY=
AI_MODEL=
AI_TIMEOUT_SECONDS=90

BOT_ENV=dev
LOG_LEVEL=INFO
```

Позже можно добавить:

```text
WEBHOOK_URL=
WEBHOOK_SECRET=
REDIS_URL=
SENTRY_DSN=
```

## Услуги и цены MVP

| Код услуги | Название | Цена |
|---|---|---:|
| `free_daily_forecast` | Бесплатный дневной прогноз | 0 Stars |
| `daily_forecast_extended` | Расширенный прогноз на день | 100 Stars |
| `personal_question` | Личный вопрос | 350 Stars |
| `compatibility` | Совместимость | 600 Stars |
| `natal_chart` | Натальная карта | 900 Stars |
| `monthly_forecast` | Прогноз на месяц | 400 Stars |

Будущие услуги:

| Код услуги | Название | Цена |
|---|---|---:|
| `weekly_forecast` | Прогноз на неделю | 250 Stars |
| `numerology` | Нумерология | 250 Stars |
| `tarot_astrology` | Таро + астрология | 300 Stars |
| `lunar_calendar_month` | Лунный календарь на месяц | 300 Stars |

## База данных

### Таблица `users`

Хранит Telegram-пользователя.

| Поле | Тип | Описание |
|---|---|---|
| `id` | integer | Внутренний ID |
| `telegram_id` | bigint | Telegram ID пользователя |
| `username` | string nullable | Username |
| `first_name` | string nullable | Имя из Telegram |
| `last_name` | string nullable | Фамилия из Telegram |
| `language_code` | string nullable | Язык Telegram |
| `is_blocked` | boolean | Заблокирован ли пользователь |
| `created_at` | datetime | Дата регистрации |
| `updated_at` | datetime | Дата обновления |

### Таблица `profiles`

Хранит астрологический профиль.

| Поле | Тип | Описание |
|---|---|---|
| `id` | integer | ID профиля |
| `user_id` | foreign key | Связь с `users` |
| `name` | string | Имя для обращений |
| `birth_date` | date nullable | Дата рождения |
| `birth_time` | time nullable | Время рождения |
| `birth_place` | string nullable | Место рождения |
| `gender` | string nullable | Пол, если пользователь указал |
| `timezone` | string nullable | Часовой пояс |
| `created_at` | datetime | Дата создания |
| `updated_at` | datetime | Дата обновления |

### Таблица `orders`

Хранит заказ на услугу.

| Поле | Тип | Описание |
|---|---|---|
| `id` | integer | ID заказа |
| `public_id` | string | Короткий публичный ID |
| `user_id` | foreign key | Пользователь |
| `service_code` | string | Код услуги |
| `status` | string | Статус заказа |
| `price_stars` | integer | Цена в Stars |
| `currency` | string | Для Stars всегда `XTR` |
| `input_data_json` | json/text | Данные для услуги |
| `result_text` | text nullable | Итоговый AI-ответ |
| `error_message` | text nullable | Ошибка, если была |
| `created_at` | datetime | Создан |
| `paid_at` | datetime nullable | Оплачен |
| `generation_started_at` | datetime nullable | Начало генерации |
| `delivered_at` | datetime nullable | Результат отправлен |
| `updated_at` | datetime | Обновлен |

### Таблица `payments`

Хранит платежи Telegram Stars.

| Поле | Тип | Описание |
|---|---|---|
| `id` | integer | ID платежа |
| `order_id` | foreign key | Заказ |
| `user_id` | foreign key | Пользователь |
| `telegram_payment_charge_id` | string nullable | ID платежа Telegram |
| `provider_payment_charge_id` | string nullable | ID провайдера, если есть |
| `invoice_payload` | string | Payload invoice |
| `currency` | string | `XTR` |
| `amount_stars` | integer | Сумма в Stars |
| `status` | string | Статус платежа |
| `raw_payload_json` | json/text nullable | Сырые данные платежа |
| `created_at` | datetime | Создан |
| `paid_at` | datetime nullable | Оплачен |
| `refunded_at` | datetime nullable | Возвращен |

### Таблица `ai_generations`

Хранит попытки AI-генерации.

| Поле | Тип | Описание |
|---|---|---|
| `id` | integer | ID генерации |
| `order_id` | foreign key nullable | Заказ |
| `user_id` | foreign key | Пользователь |
| `service_code` | string | Услуга |
| `prompt_version` | string | Версия промпта |
| `model` | string | AI-модель |
| `status` | string | Статус |
| `prompt_text` | text | Финальный промпт |
| `result_text` | text nullable | Ответ |
| `error_message` | text nullable | Ошибка |
| `tokens_input` | integer nullable | Входные токены |
| `tokens_output` | integer nullable | Выходные токены |
| `created_at` | datetime | Создана |
| `finished_at` | datetime nullable | Завершена |

### Таблица `support_requests`

Хранит обращения в поддержку.

| Поле | Тип | Описание |
|---|---|---|
| `id` | integer | ID обращения |
| `user_id` | foreign key | Пользователь |
| `order_id` | foreign key nullable | Заказ, если связан |
| `category` | string | Тема обращения |
| `message_text` | text | Сообщение пользователя |
| `status` | string | Статус |
| `created_at` | datetime | Создано |
| `closed_at` | datetime nullable | Закрыто |

### Таблица `admin_events`

Хранит важные события для аудита.

| Поле | Тип | Описание |
|---|---|---|
| `id` | integer | ID события |
| `user_id` | foreign key nullable | Пользователь |
| `order_id` | foreign key nullable | Заказ |
| `event_type` | string | Тип события |
| `message` | text | Описание |
| `payload_json` | json/text nullable | Технические данные |
| `created_at` | datetime | Дата события |

## Статусы заказа

| Статус | Значение |
|---|---|
| `created` | Заказ создан |
| `collecting_data` | Бот собирает данные |
| `waiting_payment` | Ожидается оплата |
| `paid` | Оплата получена |
| `generating` | Идет AI-генерация |
| `delivered` | Результат отправлен пользователю |
| `failed` | Ошибка |
| `refund_requested` | Пользователь запросил возврат |
| `refunded` | Возврат выполнен |
| `cancelled` | Заказ отменен |

## Статусы платежа

| Статус | Значение |
|---|---|
| `invoice_created` | Invoice создан |
| `pre_checkout_approved` | Pre-checkout подтвержден |
| `paid` | Успешная оплата |
| `failed` | Ошибка оплаты |
| `refund_requested` | Запрошен возврат |
| `refunded` | Возврат выполнен |

## Telegram Stars: логика оплаты

Для цифровых услуг внутри Telegram используем Telegram Stars.

### Создание invoice

При создании invoice:

- `currency`: `XTR`
- `provider_token`: пустая строка
- `prices`: ровно один элемент для Stars
- `payload`: внутренний ID заказа или подписанный payload

Пример payload:

```text
order:{public_order_id}:{user_id}:{service_code}
```

Лучше подписывать payload или проверять его по базе, чтобы пользователь не мог подменить услугу или сумму.

### Pre-checkout

Когда Telegram отправляет `pre_checkout_query`, бот должен ответить в течение 10 секунд.

Проверяем:

1. Заказ существует.
2. Заказ принадлежит этому пользователю.
3. Статус заказа `waiting_payment`.
4. Сумма совпадает с ценой услуги.
5. Валюта `XTR`.

Если все хорошо:

- отвечаем `ok=True`;
- ставим платежу статус `pre_checkout_approved`.

Если есть проблема:

- отвечаем `ok=False`;
- возвращаем понятное сообщение пользователю.

### Successful payment

Результат услуги выдаем только после получения `successful_payment`.

После успешной оплаты:

1. Сохраняем `telegram_payment_charge_id`.
2. Меняем статус платежа на `paid`.
3. Меняем статус заказа на `paid`.
4. Запускаем AI-генерацию.
5. После генерации отправляем результат.
6. Меняем статус заказа на `delivered`.

### Возвраты

Для возврата Stars используем `refundStarPayment`.

Для этого нужно хранить:

- `user_id`;
- `telegram_payment_charge_id`;
- сумму;
- заказ;
- причину возврата.

Возврат в MVP делает администратор вручную через админ-команду.

## Сценарии пользователя

### `/start`

1. Создать или обновить пользователя в базе.
2. Показать приветствие.
3. Показать кнопки:
   - получить прогноз;
   - посмотреть услуги;
   - заполнить профиль.

### Бесплатный дневной прогноз

1. Проверить профиль.
2. Если нет имени или даты рождения, собрать данные.
3. Создать заказ с ценой `0`.
4. Сразу запустить AI-генерацию.
5. Отправить результат.
6. Предложить расширенный прогноз за Stars.

### Платная услуга

Общий путь:

1. Пользователь выбирает услугу.
2. Бот собирает данные.
3. Бот создает заказ.
4. Бот показывает цену.
5. Бот отправляет invoice.
6. После `successful_payment` запускает генерацию.
7. Отправляет результат.
8. Показывает апсейл.

## FSM-состояния

### Профиль

- `profile_waiting_name`
- `profile_waiting_birth_date`
- `profile_waiting_birth_time`
- `profile_waiting_birth_place`
- `profile_confirm`

### Личный вопрос

- `question_waiting_area`
- `question_waiting_text`
- `question_confirm`
- `question_waiting_payment`

### Совместимость

- `compat_waiting_relationship_type`
- `compat_waiting_partner_name`
- `compat_waiting_partner_birth_date`
- `compat_waiting_partner_birth_time`
- `compat_waiting_partner_birth_place`
- `compat_confirm`
- `compat_waiting_payment`

### Натальная карта

- `natal_collecting_profile`
- `natal_confirm`
- `natal_waiting_payment`

### Прогноз на месяц

- `monthly_waiting_area`
- `monthly_confirm`
- `monthly_waiting_payment`

## AI-генерация

### Общая логика

1. Берем данные заказа.
2. Выбираем шаблон промпта из `AI_PROMPTS.md`.
3. Подставляем переменные.
4. Отправляем запрос в AI-сервис.
5. Сохраняем результат в `ai_generations`.
6. Прогоняем ответ через проверку безопасности.
7. Сохраняем финальный результат в `orders.result_text`.
8. Отправляем пользователю.

### Повторные попытки

Если генерация не удалась:

1. Повторить 1 раз автоматически.
2. Если снова ошибка, поставить заказу статус `failed`.
3. Уведомить администратора.
4. Сообщить пользователю, что заказ сохранен.

### Ограничения

AI-ответ не должен:

- обещать точные события;
- давать медицинские, юридические, инвестиционные советы;
- пугать пользователя;
- давить на покупку;
- выдавать профессиональную консультацию;
- советовать резкие действия как единственно правильный путь.

## Админ-уведомления

Администратор получает сообщения в Telegram.

### События

- Новый пользователь.
- Новый заказ.
- Успешная оплата.
- Ошибка оплаты.
- Ошибка AI-генерации.
- Запрос поддержки.
- Запрос возврата.

### Формат уведомления о заказе

```text
📝 Новый заказ

ID: {order_public_id}
Пользователь: {user_name}
Telegram ID: {telegram_id}
Услуга: {service_code}
Цена: {price_stars} Stars
Статус: {status}
```

### MVP-админ-команды

- `/admin_orders` — последние заказы
- `/admin_order <id>` — подробности заказа
- `/admin_user <telegram_id>` — пользователь
- `/admin_retry <order_id>` — повторить генерацию
- `/admin_refund <order_id>` — оформить возврат Stars

Админ-команды доступны только Telegram ID из `ADMIN_TELEGRAM_ID`.

## Валидация данных

### Дата рождения

Принимаемый формат:

```text
ДД.ММ.ГГГГ
```

Проверки:

- дата существует;
- дата не в будущем;
- возраст не выглядит невозможным;
- для странных дат показываем мягкую ошибку.

### Время рождения

Принимаемый формат:

```text
ЧЧ:ММ
```

Можно пропустить.

### Место рождения

На MVP просто текстовая строка.

Позже можно добавить:

- автодополнение городов;
- геокодинг;
- часовой пояс по месту рождения.

### Личный вопрос

Проверки:

- не пустой;
- не слишком короткий;
- не слишком длинный;
- если вопрос явно медицинский, юридический, инвестиционный или опасный, отвечаем безопасной заготовкой и предлагаем переформулировать.

## Тексты и промпты

Используем документы:

- `BOT_TEXTS.md` — тексты интерфейса;
- `AI_PROMPTS.md` — шаблоны AI-ответов;
- `PRODUCT_MATRIX.md` — продуктовая логика;
- `PRICING_AND_PAYMENTS.md` — цены и платежи;
- `BOT_FLOW.md` — сценарий пользователя.

В коде тексты лучше хранить в отдельном модуле:

```text
bot/texts/ru.py
```

Промпты лучше хранить отдельно:

```text
bot/services/prompts.py
```

## Логирование

Логируем:

- старт бота;
- новые пользователи;
- создание заказов;
- создание invoice;
- pre-checkout;
- successful payment;
- запуск AI-генерации;
- ошибки AI;
- отправку результата;
- запросы поддержки.

Нельзя логировать:

- секретные токены;
- API-ключи;
- лишние персональные данные без необходимости.

## Безопасность

1. `BOT_TOKEN` и `AI_API_KEY` только в `.env`.
2. `.env` не должен попадать в git.
3. Админ-команды только для разрешенного Telegram ID.
4. Результат платной услуги отправлять только после `successful_payment`.
5. Payload invoice проверять по базе.
6. Хранить `telegram_payment_charge_id` для возвратов.
7. Делать резервную копию базы перед публичным запуском.

## Обработка ошибок

### Ошибка Telegram API

1. Записать ошибку в лог.
2. Если пользователь заблокировал бота, отметить `is_blocked=True`.
3. Если ошибка временная, попробовать повторить.

### Ошибка AI

1. Повторить генерацию 1 раз.
2. Если повтор не помог, поставить заказ `failed`.
3. Уведомить администратора.
4. Сообщить пользователю, что заказ сохранен.

### Ошибка базы

1. Записать критическую ошибку.
2. Не подтверждать оплату, если не можем надежно сохранить заказ.
3. Уведомить администратора.

## Минимальные тесты

### Unit-тесты

- парсинг даты;
- парсинг времени;
- расчет цены услуги;
- генерация payload;
- проверка payload;
- переходы статусов заказа;
- выбор промпта по услуге.

### Интеграционные тесты

- создание пользователя;
- создание заказа;
- успешная оплата;
- сохранение платежа;
- генерация результата;
- повтор генерации при ошибке;
- возврат Stars через мок.

### Ручной чеклист

1. `/start` открывает приветствие.
2. Пользователь может заполнить профиль.
3. Бесплатный прогноз работает без оплаты.
4. Платная услуга создает invoice.
5. После оплаты результат выдается.
6. Без оплаты результат не выдается.
7. Администратор получает уведомление о заказе.
8. Ошибка AI не теряет заказ.
9. `/support`, `/terms`, `/paysupport` работают.
10. Кнопка "Назад" не ломает сценарий.

## План разработки MVP

### Этап 1. Каркас проекта

1. Создать структуру проекта.
2. Настроить зависимости.
3. Подключить конфиг `.env`.
4. Запустить бота в long polling.
5. Сделать `/start` и главное меню.

### Этап 2. База данных

1. Создать модели.
2. Создать таблицы.
3. Добавить репозитории.
4. Сохранять пользователей.
5. Сохранять профиль.

### Этап 3. Бесплатный прогноз

1. Сбор имени и даты рождения.
2. Создание бесплатного заказа.
3. Подключение AI-генерации.
4. Выдача результата.

### Этап 4. Платные заказы

1. Создание заказа.
2. Создание invoice в Stars.
3. Обработка `pre_checkout_query`.
4. Обработка `successful_payment`.
5. Запуск генерации после оплаты.

### Этап 5. MVP-услуги

1. Личный вопрос.
2. Совместимость.
3. Натальная карта.
4. Прогноз на месяц.

### Этап 6. Админ и поддержка

1. Админ-уведомления.
2. `/support`.
3. `/paysupport`.
4. `/terms`.
5. Команда повтора генерации.
6. Команда возврата.

### Этап 7. Тестовый запуск

1. Проверить все сценарии.
2. Проверить тестовые платежи Stars.
3. Проверить ошибки генерации.
4. Проверить UX текстов.
5. Собрать правки.

## Критерии готовности MVP

MVP считается готовым, когда:

1. Бот запускается без ошибок.
2. Пользователь может пройти путь от `/start` до результата.
3. Бесплатный прогноз работает.
4. Минимум одна платная услуга работает через Stars.
5. Заказы и платежи сохраняются.
6. Результат не выдается без успешной оплаты.
7. Администратор получает уведомления.
8. Есть `/terms`, `/support`, `/paysupport`.
9. Ошибка AI не теряет оплаченный заказ.
10. Есть понятная инструкция запуска.

## Источники по Telegram Payments

- Telegram Stars для цифровых товаров и услуг: https://core.telegram.org/bots/payments-stars
- Telegram Bot API: Payments: https://core.telegram.org/bots/api#payments
- `sendInvoice`: https://core.telegram.org/bots/api#sendinvoice
- `answerPreCheckoutQuery`: https://core.telegram.org/bots/api#answerprecheckoutquery
- `refundStarPayment`: https://core.telegram.org/bots/api#refundstarpayment
