FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (git for commit/push)
RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

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
