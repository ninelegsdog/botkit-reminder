FROM python@sha256:09f7da3bc104798d0afb40bc08d23ab2da20a76130cec1f2ef170848f5d85217 AS builder
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml ./
RUN --mount=type=secret,id=BOTKIT_CORE_TOKEN bash <<'EOF'
    set -e
    if [ -f /run/secrets/BOTKIT_CORE_TOKEN ]; then
      git config --global url."https://x-access-token:$(cat /run/secrets/BOTKIT_CORE_TOKEN)@github.com/ninelegsdog/botkit-core".insteadOf "https://github.com/ninelegsdog/botkit-core"
    fi
    pip install --no-cache-dir -e ".[dev]"
    rm -f ~/.gitconfig
    apt-get purge -y --auto-remove git
    rm -rf /var/lib/apt/lists/*
EOF

FROM python@sha256:09f7da3bc104798d0afb40bc08d23ab2da20a76130cec1f2ef170848f5d85217 AS runtime
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
RUN mkdir -p /app/data /app/backups && chown -R appuser:appgroup /app
USER appuser
EXPOSE 8080
ARG PORT
CMD ["python", "bot.py"]
