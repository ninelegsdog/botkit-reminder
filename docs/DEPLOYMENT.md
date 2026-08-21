# Deployment

## Environment variables

```env
TELEGRAM_BOT_TOKEN=123:ABC
TELEGRAM_WEBHOOK_SECRET=supersecret
TELEGRAM_ADMIN_IDS=123456,789012
ADMIN_PASSWORD_HASH=<sha256 hash>
DATABASE_URL=sqlite+aiosqlite:///./data/reminder.db
REDIS_URL=redis://localhost:6379/0
TZ=Europe/Moscow
SCHEDULER_INTERVAL_SECONDS=30
LOG_LEVEL=INFO
```

## Docker

```bash
docker build -t botkit-reminder .
docker compose up -d
```

## Local dev

```bash
python -m pip install -e ".[dev]"
export $(cat .env | xargs)
python bot.py
```

## Health checks

- `GET /healthz` — liveness
- `GET /readyz` — readiness
- `GET /metrics` — Prometheus

## Security

- `read_only: true`, `cap_drop: ALL`, `no-new-privileges: true`
- Secrets via `.env.age`
- CI: Trivy + CodeQL
