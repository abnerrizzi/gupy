FROM python:3.12-alpine

RUN apk add --no-cache sqlite && \
    adduser -D appuser

WORKDIR /app

COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

COPY app/ app/
COPY *.sh *.sql ./

RUN chown -R appuser:appuser /app && \
    chmod +x *.sh

USER appuser

CMD ["./run_scrap.sh", "out"]