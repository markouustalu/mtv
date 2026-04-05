# MTV - Simple IPTV Streaming Server
# Multi-stage build for smaller image

# Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY requirements.txt .
COPY src/ src/

# Install Python dependencies
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt
RUN pip wheel --no-cache-dir --no-deps . -w /build/wheels

# Runtime stage
FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --gid 1000 mtv \
    && useradd --uid 1000 --gid mtv --shell /bin/bash --create-home mtv

WORKDIR /app

# Copy wheels from builder and install
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl \
    && rm -rf /wheels

# Copy source code
COPY --chown=mtv:mtv src/ /app/src/
COPY --chown=mtv:mtv config/ /app/config/

# Create necessary directories
RUN mkdir -p /app/logs \
    && chown -R mtv:mtv /app/logs

# Switch to non-root user
USER mtv

# Expose port
EXPOSE 8555

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8555/health')" || exit 1

# Run the application
CMD ["python", "-m", "mtv.main"]
