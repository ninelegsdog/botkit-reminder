FROM python:3.12-slim

RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

RUN mkdir -p /app/data /app/backups && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

CMD ["python", "bot.py"]
