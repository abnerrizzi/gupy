FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    FIREFOX_VERSION=115.13.0

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

RUN curl -sL https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz | tar -xzf - -C /usr/local/bin && \
    chmod +x /usr/local/bin/geckodriver

WORKDIR /app

COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/
COPY run_scrap.sh /app/
COPY sqlite-init.sql /app/
RUN chmod +x /app/run_scrap.sh

CMD ["./run_scrap.sh", "out"]