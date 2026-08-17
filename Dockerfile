FROM python:3.10-slim

WORKDIR /app

# Install dependencies and system tools in one go
COPY requirements.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends librsvg2-bin \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Make healthcheck script executable
RUN chmod +x healthcheck.sh

# Excluded from the build context by .dockerignore; the volume mount shadows
# this in production, but the app writes here directly and does not mkdir.
RUN mkdir -p /app/config

# Optional: Create a non-root user for extra security
#RUN useradd -ms /bin/bash hambotuser
#USER hambotuser

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["/app/healthcheck.sh"]

CMD [ "python", "./hambot.py" ]
