FROM python@sha256:09f7da3bc104798d0afb40bc08d23ab2da20a76130cec1f2ef170848f5d85217 AS builder
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
# uv is used only to read uv.lock and emit a constraints file. It is deleted again
# before the layer is sealed, and the runtime stages copy site-packages only, so the
# binary never reaches the shipped image.
COPY --from=ghcr.io/astral-sh/uv@sha256:cdc6093146eb3ff6a40107b38f008b789e050e77ad87865e381d9917da55a168 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN --mount=type=secret,id=BOTKIT_CORE_TOKEN bash <<'EOF'
    set -e
    if [ -f /run/secrets/BOTKIT_CORE_TOKEN ]; then
      git config --global url."https://x-access-token:$(cat /run/secrets/BOTKIT_CORE_TOKEN)@github.com/ninelegsdog/botkit-core".insteadOf "https://github.com/ninelegsdog/botkit-core"
    fi
    # Exact versions from uv.lock. `pip install .` alone resolved `>=` ranges against
    # whatever the index held at build time, so two builds of one revision could differ
    # and a rebuild months later would pick up versions nobody reviewed. `--locked` fails
    # the build if pyproject.toml and uv.lock disagree.
    uv export --locked --no-emit-project --no-hashes --all-extras -o /tmp/constraints.txt
    # Drop botkit-core itself. uv always exports a git dependency as its *resolved commit*,
    # while pyproject.toml pins it by tag, so pip is handed two different requirements for
    # the same distribution and refuses: "Cannot install ... conflicting dependencies".
    # core is already pinned by tag where it matters; the line removed here is redundant,
    # not lost - and its own dependencies stay constrained, which is what this file is for.
    grep -v '^botkit-core @ ' /tmp/constraints.txt > /tmp/c.txt && mv /tmp/c.txt /tmp/constraints.txt
    pip install --no-cache-dir -c /tmp/constraints.txt -e ".[dev]"
    rm -f ~/.gitconfig /tmp/constraints.txt /usr/local/bin/uv
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
ARG BUILD_SHA
ENV BUILD_SHA=$BUILD_SHA
CMD ["python", "bot.py"]
