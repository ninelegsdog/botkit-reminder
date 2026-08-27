FROM python:3.12-slim AS builder
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

FROM python:3.12-slim AS runtime
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
RUN mkdir -p /app/data /app/backups && chown -R appuser:appgroup /app
USER appuser
EXPOSE 8080
ARG PORT
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request as u; u.urlopen('http://localhost:${PORT}/health')"
CMD ["python", "bot.py"]