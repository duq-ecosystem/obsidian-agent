# Obsidian Agent Dockerfile
# DUQ Obsidian specialist agent

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy duq-agent-core first (dependency)
COPY --from=duq-agent-core /app /opt/duq-agent-core

# Install duq-agent-core
RUN pip install --no-cache-dir /opt/duq-agent-core

# Copy project files
COPY pyproject.toml .
COPY constitution.yaml .
COPY src/ src/

# Install obsidian-agent
RUN pip install --no-cache-dir -e .

# Environment variables
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
CMD ["obsidian-agent"]
