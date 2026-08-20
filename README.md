# BotKit Reminder

Telegram-бот напоминаний и рассылок. Часть портфолио из 9 ботов на freelance.ru.

## Возможности

- Одноразовые и повторяющиеся напоминания
- Рассылки подписчикам с сегментацией
- Админка в чате (пароль, статистика, управление подписчиками)
- Планировщик с интервалом 30 секунд
- Поддержка 152-ФЗ (удаление по запросу, аудит)
- Docker, webhook (prod), polling (dev)

## Стек

- Python 3.13
- aiogram 3.30+
- SQLAlchemy + aiosqlite (WAL)
- Redis-FSM
- APScheduler
- Prometheus /metrics

## Запуск

```bash
cp .env.example .env
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
alembic upgrade head
python -m botkit_reminder.bot
```

## Тесты

```bash
pytest
```

## Деплой

```bash
docker compose up -d
```

## Лицензия

MIT
