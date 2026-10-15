# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added


- The repository presents itself as it is. The README became a front page — pitch,
  badges, a table of contents and user-facing sections — and issue forms plus a
  pull-request template now ask for the evidence this project acts on: what was
  run, what was expected, and how "done" would be able to fail.
- Governance layer brought to the family standard: `CONTRIBUTING.md`,
  `SECURITY.md`, `CODE_OF_CONDUCT.md`, `AGENTS.md`, `.editorconfig`,
  `.gitattributes` and `CODEOWNERS`.
- `scripts/check-repo-contract.py` checks this repository against the shared
  contract, and `scripts/check-repo-contract_test.py` proves that checker can
  fail. A gate that has never gone red is an assumption, not a gate.
- Long-form documentation that already existed but was not linked is now linked from the front page: `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`.

### Changed


- Line endings are pinned to LF by `.gitattributes`, so a CRLF contributor no
  longer turns every touched line into a diff.

### Fixed

- Админ-гард на «📊 Статистика» и «👥 Подписчики» не срабатывал: декоратор
  `@admin_only` стоял ВЫШЕ `@router.message(...)`, поэтому роутер регистрировал
  незащищённый обработчик, и не-админ читал статистику и список подписчиков
  (user_id, username, имя). Порядок декораторов исправлен (роутер сверху, гард
  снизу — как у соседних обработчиков); регресс — `tests/test_admin_guard_order.py`,
  строчная проверка, что гард идёт последним декоратором у каждого обработчика.

- `ThrottlingMiddleware` passed context to the next handler as `handler(event, **data)`
  (aiogram 2 convention) while running on aiogram 3, where the wrapped handler is
  `handler(event, data)`. Every text update raised
  `TypeError: ... got an unexpected keyword argument 'dispatcher'` and the user never got
  a reply. Now `handler(event, data)`; regression covered by
  `tests/test_throttling_contract.py`.

- `README-testing.md` was unreachable from the README in every bot of the family
  except one. A document nobody can reach is a document nobody reads; it is linked
  from the front page now.

### CI

- 2026-09-14 — повторный запуск CI и очистка прогонов с 0 jobs.

## [1.0.0] - 2026-08-28

### Added
- Продакшен-релиз 1.0.0: напоминания и рассылки, админка в чате, поддержка 152-ФЗ.
  Теги `v1.0.1`–`v1.0.6` — итерации релизной линии 1.0.x (детали в истории коммитов).

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
