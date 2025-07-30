FROM python:3.10-slim

WORKDIR /app

# Install dependencies and system tools in one go
COPY requirements.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends librsvg2-bin \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Optional: Create a non-root user for extra security
#RUN useradd -ms /bin/bash hambotuser
#USER hambotuser

CMD [ "python", "./hambot.py" ]
