FROM python:3.12-slim AS builder
RUN pip install uv
COPY pyproject.toml .
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
WORKDIR /app
COPY --from=builder /root/.local /home/appuser/.local
COPY . .
RUN chown -R appuser:appgroup /app
USER appuser
EXPOSE 8080
CMD ["python", "-m", "botkit_reminder.bot", "--webhook"]
