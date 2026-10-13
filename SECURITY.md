# Security Policy

## Supported Versions

The current version is **1.0.6** (`pyproject.toml`); the production release line
is `1.0.x`, first cut as 1.0.0 on 2026-08-28.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| 0.2.x   | :x:                |
| 0.1.x   | :x:                |

Security fixes land on `main` and are cut from there. There is no
long-term-support branch, so an unpatched 0.x report is not a regression —
0.x predates the production release and is no longer deployed.

## Reporting a Vulnerability

Report security issues to algtro@users.noreply.github.com.

## Security Measures

- Webhook validation via `X-Telegram-Bot-Api-Secret-Token`
- `.env.age` for secrets (age encryption)
- Docker hardening: non-root user, read_only, cap_drop ALL
- Trivy scan in CI
- Dependabot + SBOM
- 152-ФЗ compliance: deletion on request, audit log, role-based access
- HTML-escape for user input
- Token masking in logs
