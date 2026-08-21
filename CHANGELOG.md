# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-21

### Added
- Unit of Work pattern with DI container (`src/core/uow/`, `src/core/di/`)
- Prometheus metrics for scheduler, errors, webhooks (`src/core/metrics.py`)
- CI/CD pipeline with Trivy + CodeQL (`.github/workflows/ci.yml`)
- Health checks (`/healthz`, `/readyz`)
- Graceful shutdown for webhook mode
- Configuration validation on startup
- Integration test scaffolding for PostgreSQL/Redis
- Architecture docs and deployment guide (`docs/`)
- BotFather commands setup (`src/core/commands.py`)
- Redis cache utility (`src/core/cache.py`)
- Tests for config, errors, logging, metrics, webhook, repositories, uow

### Changed
- All services now accept `UnitOfWork` instead of raw `AsyncSession`
- Scheduler uses repositories instead of raw SQLAlchemy queries
- Handlers use `async with UnitOfWork()` instead of `get_session()`
- Webhook handler now processes Telegram updates via dispatcher
- Added `prometheus-client` to dependencies

### Fixed
- Removed unused imports (ruff fixes)
- Fixed mypy strict mode compliance

## [0.1.0] - 2026-08-20

### Added
- Initial scaffold for botkit-reminder
- aiogram 3.x bot with polling mode
- SQLAlchemy async with SQLite
- APScheduler for reminders
- Basic handlers for reminders and subscriptions
- Admin panel with stats
- Tests with pytest
