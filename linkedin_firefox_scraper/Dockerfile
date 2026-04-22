FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    FIREFOX_VERSION=115.13.0

# ---- Base deps (rarely change - cached first) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    firefox-esr \
    wget \
    gnupg \
    ca-certificates \
    procps \
    sqlite3 \
    bzip2 \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- geckodriver (rarely change - cached) ----
RUN curl -sL https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz | tar -xzf - -C /usr/local/bin && \
    chmod +x /usr/local/bin/geckodriver

WORKDIR /app

# ---- Python deps (change only when requirements.txt changes - cached) ----
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ---- App code (changes most frequently - cached last) ----
COPY app/main.py /app/main.py
COPY run_scrap.sh /app/
COPY sqlite-init.sql /app/
RUN chmod +x /app/run_scrap.sh

# ---- Debug tools (OPTIONAL - only rebuild when explicitly changed) ----
# VNC for watching the browser:
RUN apt-get update && apt-get install -y --no-install-recommends x11vnc xvfb fluxbox && rm -rf /var/lib/apt/lists/*

CMD ["./run_scrap.sh", "out"]