# BotKit Reminder

A reminders and broadcasts bot: one-off and recurring reminders, plus segmented newsletters.

[![CI](https://github.com/ninelegsdog/botkit-reminder/actions/workflows/ci.yml/badge.svg)](https://github.com/ninelegsdog/botkit-reminder/actions/workflows/ci.yml) [![License](https://img.shields.io/github/license/ninelegsdog/botkit-reminder.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.12-339933.svg)](#quick-start)

> **Status.** Runs in production on webhook transport, with Alembic-managed migrations. State: **production**.

## Contents

- [What it does](#what-it-does)
- [Features](#features)
- [Stack](#stack)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Running in production](#running-in-production)
- [Testing](#testing)
- [How this is built](#how-this-is-built)
- [Backups](#backups)
- [Development process](#development-process)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)

## What it does

Part of a family of nine production Telegram bots on Python. Reminder holds personal data by design, so deletion on request and an audit trail are part of the feature rather than an afterthought.

This repository carries two long-form documents that predate the front page: `docs/ARCHITECTURE.md` and `docs/DEPLOYMENT.md`. They are linked below rather than folded into the README, because they are still maintained separately.

## Features

- **One-off and recurring reminders** — The scheduler runs both without the user having to know which kind they created.
- **Segmented broadcasts** — Newsletters go to a segment of subscribers, not to everyone by default.
- **In-chat admin panel** — Password-gated, with statistics and subscriber management.
- **Scheduler on a 30-second interval** — `src/core/` carries the scheduler; a short interval keeps reminder drift small.
- **Russian personal-data law support** — 152-FZ: deletion on request, an audit log, and role-based access.
- **Docker, webhook in production, polling in development** — The operational surface every bot in this family carries.

## Stack

- Python 3.12+
- aiogram 3.30+
- SQLAlchemy + aiosqlite (WAL)
- Redis-FSM
- APScheduler
- Prometheus /metrics

## Quick start

```bash
cp .env.example .env
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
alembic upgrade head
python -m bot
```

Requires **Python 3.12** and [`uv`](https://docs.astral.sh/uv/). Copy
`.env.example` to `.env` and fill in the bot token and admin ids before starting.

## Configuration

Every variable is declared in [`.env.example`](.env.example); nothing is read that
is not declared there.

| Variable | Required | Holds a secret |
|---|---|---|
| `ADMIN_PASSWORD_HASH` | no | yes |
| `DATABASE_URL` | no | no |
| `LOG_LEVEL` | no | no |
| `METRICS_PORT` | no | no |
| `REDIS_URL` | no | no |
| `SCHEDULER_INTERVAL_SECONDS` | no | no |
| `SENTRY_DSN` | no | yes |
| `TELEGRAM_ADMIN_IDS` | no | no |
| `TELEGRAM_BOT_TOKEN` | no | yes |
| `TELEGRAM_STARS_PROVIDER_ENABLED` | no | no |
| `TELEGRAM_WEBHOOK_SECRET` | no | yes |
| `YOOKASSA_SECRET_KEY` | no | yes |
| `YOOKASSA_SHOP_ID` | no | no |

"Holds a secret" is classified by variable name, not by reading the value. Treat every `yes` as sensitive regardless.

Secrets never enter git: `.env` is ignored, and CI runs a gitleaks gate over the
history.

## Running in production

The bot runs behind a webhook with TLS and a health check. `deploy/` holds the
production compose file and its own `.env.example`.

```bash
cd deploy && cp .env.example .env   # fill in, then bring the stack up
```

## Testing

```bash
pytest
```

165 test functions across 33 files run offline in
CI — no Telegram account and no network. Tests that need either are marked `req`
and stay skipped unless `RUN_TELEGRAM_E2E=1` is set, so a fresh clone is green with
no secrets.

The full guide is **[README-testing.md](README-testing.md)**: test markers, the offline-versus-network split, the opt-in real-Telegram E2E suite, and the webhook secret contract.

CI also gates the lockfile (`uv lock --check`), runs gitleaks over the history,
scans the filesystem with Trivy, and validates the k6 load script.

## How this is built

```
src/
├── admin/  handlers.py, service.py
├── core/  auth.py, bot_factory.py, cache.py, callbacks.py, commands.py, config.py
└── reminder/  handlers.py, models.py, scheduler.py, service.py
```

`botkit-core` is a separate published library carrying the shared runtime. This
repository depends on it by tag, not by path — see `pyproject.toml`.

## Backups

Backups and restore are a production-wide concern (systemd timers, offsite restic,
one Redis shared across bots), not a script inside a repository. The current
procedure and its caveats live in
[`botkit-monitoring/ops/backup/RESTORE.md`](https://github.com/ninelegsdog/botkit-monitoring/blob/main/ops/backup/RESTORE.md).

## Development process

This project was built in an AI-native process: the implementation was produced by
coding agents under human-led engineering control — requirement slots, constraints
and acceptance criteria defined in advance, then specification, generation, run,
check, fix.

My role in the project:

- product definition and user-facing scenarios;
- decomposition into independent engineering stages;
- context engineering: the instructions, constraints and working rules agents run under;
- management of the context window between iterations;
- the loop of specification → generation → run → verification → correction;
- validation, testing and review;
- control of repository structure, configuration, documentation and run reproducibility.

Implementation code was generated with AI coding agents under human-led engineering
control. The full description of the process, the `AGENTS.md` template, and the
review checklists for AI-written code and secrets are in
[agentic-development-playbook](https://github.com/ninelegsdog/agentic-development-playbook).

## Documentation

- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** — Deployment.
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Architecture.
- **[README-testing.md](README-testing.md)** — test markers, offline vs network suites, opt-in real-Telegram E2E, webhook secret contract.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — how to set up, what CI checks, what a PR must show.
- **[SECURITY.md](SECURITY.md)** — how to report a vulnerability and what is in scope.
- **[AGENTS.md](AGENTS.md)** — the rules a coding agent working here must follow.
- **[CHANGELOG.md](CHANGELOG.md)** — what changed, and when.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: install with `uv`, run `pytest`
and `pre-commit run --all-files`, and explain why rather than what — the diff
already shows what.

## Security

Do not open a public issue for a security problem. See [SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).
