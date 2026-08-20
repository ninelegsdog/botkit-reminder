# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

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
