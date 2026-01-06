FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Claude Code
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Copy and install Python package
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

# Set environment
ENV REPO_PATH=/repo
ENV PORT=8788
ENV HOME=/root

EXPOSE 8788

# Run SSE server
CMD ["goals-mcp"]
