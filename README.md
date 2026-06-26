# Astrobot Telegram

Telegram-бот «Звёзды шепчут» для персональных астрологических и символических разборов.

Бот уже умеет работать с профилем пользователя, Telegram Stars, историей заказов, админскими командами и генерацией текстов через OpenAI или безопасный локальный demo-режим.

## Возможности для пользователя

- 🎁 бесплатный персональный прогноз на сегодня;
- 🌙 подробный прогноз на месяц;
- 💌 ответ на личный вопрос;
- 🧩 совместимость двух людей;
- 🪐 натальная карта с уточнением времени рождения, жизненного этапа и главного фокуса;
- 🔢 нумерологический разбор;
- 🃏 Таро + астрология;
- 📦 раздел «Мои заказы» с сохранёнными результатами;
- 📄 условия использования, поддержка и поддержка по оплате.

## Важные файлы

- `bot/` — код бота;
- `tests/` — автоматические проверки;
- `.env.example` — пример настроек без секретов;
- `.env` — реальные секреты и настройки, не добавляется в Git;
- `astrobot.db` — локальная база данных, не добавляется в Git.

## Локальный запуск

1. Скопируй `.env.example` в `.env` и заполни реальные значения.
2. Установи зависимости:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Запусти бота:

```powershell
.\.venv\Scripts\python.exe -m bot.main
```

Для остановки нажми `Ctrl+C`. Сообщения `CancelledError` и `KeyboardInterrupt` после остановки — нормальная реакция Python на ручное завершение процесса.

## Проверки перед отправкой на сервер

```powershell
git status
.\.venv\Scripts\python.exe -m unittest discover tests
git diff --check
```

Если локальный Python в `.venv` снова капризничает из-за пути Windows/OneDrive, можно запускать тесты через установленный в системе Python или временное тестовое окружение, как мы уже делали раньше.

## Как обновлять бота на сервере

Обычный порядок такой:

1. Внести и проверить изменения локально.
2. Сохранить их в Git:

```powershell
git add .
git commit -m "Краткое описание изменений"
git push
```

3. На сервере DigitalOcean выполнить:

```bash
cd /opt/astrobot/app
sudo -u astrobot git pull --ff-only
sudo -u astrobot .venv/bin/python -m pip install -r requirements.txt
sudo systemctl restart astrobot
sudo systemctl is-active astrobot
sudo journalctl -u astrobot -n 50 --no-pager
```

Файлы `.env` и `astrobot.db` живут на сервере отдельно и не перезаписываются обычным `git pull`.

## AI-режим

Настраивается в `.env`:

```text
AI_PROVIDER=demo
AI_API_KEY=
AI_MODEL=gpt-4.1-mini
```

- `demo` — безопасная локальная генерация без внешнего API;
- `openai` — генерация через OpenAI API.

Для боевого режима с платными услугами нужен `AI_PROVIDER=openai` и заполненный `AI_API_KEY`.

## Telegram Stars

Режим оплаты задаётся в `.env`:

```text
PAYMENTS_MODE=demo
SUPPORT_USERNAME=
ADMIN_TELEGRAM_ID=
```

- `demo` — счета не создаются, услуги работают бесплатно;
- `stars_test` — создаётся настоящий счёт на 1 Star для проверки оплаты;
- `stars` — используются реальные цены каталога.

Текущие цены каталога:

- личный вопрос — 350 Stars;
- совместимость — 600 Stars;
- прогноз на месяц — 400 Stars;
- натальная карта — 900 Stars;
- Таро + астрология — 300 Stars;
- нумерология — 250 Stars.

Для `PAYMENTS_MODE=stars` обязательно заполнить `ADMIN_TELEGRAM_ID`, `SUPPORT_USERNAME`, `AI_PROVIDER=openai` и `AI_API_KEY`.

Пользователь с Telegram ID из `ADMIN_TELEGRAM_ID` может проверять платные услуги без списания Stars. Для него бот показывает админ-проверку и сразу создаёт результат, а для остальных пользователей оплата работает в обычном режиме.

## Админские команды

Доступны только Telegram ID из `ADMIN_TELEGRAM_ID`:

- `/admin` — справка;
- `/admin_stats` — статистика бота;
- `/admin_orders` — последние заказы;
- `/admin_order <ID>` — подробности заказа;
- `/admin_user <Telegram ID>` — данные пользователя;
- `/admin_retry <ID>` — повторить генерацию оплаченного заказа после ошибки;
- `/admin_refund <ID>` — вернуть пользователю Stars через Telegram.

## Безопасность

- Никогда не публикуй `.env`.
- Не отправляй токен бота и API-ключи в переписке.
- Не добавляй `astrobot.db` в Git: там могут быть пользовательские данные и история заказов.
- Перед боевым запуском проверь, что на сервере нет дубликатов строк в `.env`, особенно `PAYMENTS_MODE`.

## Полезные команды сервера

Проверить статус:

```bash
systemctl status astrobot --no-pager
```

Посмотреть последние логи:

```bash
journalctl -u astrobot -n 100 --no-pager
```

Перезапустить:

```bash
systemctl restart astrobot
```
