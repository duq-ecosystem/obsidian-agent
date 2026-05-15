# Obsidian Agent Dockerfile
# DUQ Obsidian specialist agent

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
RUN pip install --no-cache-dir uv

# Install duq-agent-core first (local dependency)
COPY duq-agent-core/pyproject.toml duq-agent-core/README.md /duq-agent-core/
COPY duq-agent-core/src/ /duq-agent-core/src/
RUN uv pip install --system /duq-agent-core

# Copy obsidian-agent files (source must be copied BEFORE editable install)
COPY obsidian-agent/pyproject.toml obsidian-agent/README.md ./
COPY obsidian-agent/src/ ./src/
COPY obsidian-agent/constitution.yaml ./

# Install obsidian-agent as editable with dev dependencies
RUN uv pip install --system -e ".[dev]"

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV OBSIDIAN_AGENT_PORT=9001
ENV OBSIDIAN_AGENT_HOST=0.0.0.0
ENV OBSIDIAN_AGENT_REDIS_URL=redis://redis:6379
ENV OBSIDIAN_VAULT_PATH=/vault
ENV OBSIDIAN_AGENT_CONSTITUTION_PATH=/app/constitution.yaml
ENV OBSIDIAN_AGENT_LOG_LEVEL=INFO

# Expose port
EXPOSE 9001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9001/.well-known/agent-card.json || exit 1

# Run agent
CMD ["python", "-m", "obsidian_agent.main"]
