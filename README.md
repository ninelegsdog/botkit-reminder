# BotKit Reminder

Telegram-бот напоминаний и рассылок. Часть портфолио из 9 Telegram-ботов.

Живой бот: @ReminderKitBot

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

## Development process

Проект создан в AI-native процессе разработки: код производили AI coding-агенты
в настроенном мной agent harness — то есть по слотам требований, инструкций, ограничений
и критериев приёмки, которые я задал заранее.

Моя роль в проекте:

- продуктовая постановка и пользовательские сценарии;
- декомпозиция задачи на самостоятельные инженерные этапы;
- context engineering: инструкции, ограничения и рабочие правила для агентов;
- управление контекстным окном между итерациями;
- цикл «спецификация → генерация → запуск → проверка → исправление»;
- валидация результата, тестирование, ревью;
- контроль структуры репозитория, конфигурации, документации и воспроизводимости запуска.

Implementation code was generated with AI coding agents under human-led engineering control.

Полное описание процесса, шаблон `AGENTS.md` и чек-листы ревью AI-кода и секретов —
в репозитории [agentic-development-playbook](https://github.com/ninelegsdog).
