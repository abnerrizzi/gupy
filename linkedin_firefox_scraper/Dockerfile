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
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz \
    && tar -xf geckodriver-v0.34.0-linux64.tar.gz -C /usr/local/bin \
    && rm geckodriver-v0.34.0-linux64.tar.gz

RUN chmod +x /usr/local/bin/geckodriver

WORKDIR /app

COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/
COPY *.sh /app/
COPY sqlite-init.sql /app/

RUN chmod +x /app/*.sh

CMD ["./run_scrap.sh", "out"]