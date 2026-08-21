# Architecture

## Overview

Telegram bot for reminders and newsletters built with aiogram 3.x, SQLAlchemy 2.x async, APScheduler, and FastAPI for webhook mode.

## Layers

- `src/core/` — framework glue: config, database session factory, error handler, logging, metrics, UoW, DI, webhook
- `src/reminder/` — domain: models, repositories, services, handlers, scheduler
- `src/admin/` — admin panel handlers and service
- `bot.py` — application entrypoint: polling vs webhook, lifespan, metrics

## Data flow

1. Update arrives via `getSessionWebhook` or `getSessionPolling`.
2. Router resolves handler → service → repository → `AsyncSession`.
3. `UnitOfWork` wraps session: commit on success, rollback on exception.
4. Scheduler ticks every `scheduler_interval_seconds`, queries due reminders, sends via callback.

## Storage

- Primary: SQLite (dev) / PostgreSQL (prod) via SQLAlchemy async.
- Job store: `SQLAlchemyJobStore` in same DB.
- Cache/optional: Redis for future throttling/caching.

## Observability

- Structured logs: `structlog` JSON.
- Metrics: Prometheus counters/gauges exposed on `:9090/metrics`.
- Health: `/healthz`, `/readyz`.

## Error handling

- Global handler catches `TelegramRetryAfter`, `TelegramNetworkError`.
- `RetryMiddleware` retries transient errors.
- Scheduler logs tick failures and continues.
