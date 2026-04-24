FROM python:3.12-alpine

RUN apk add --no-cache sqlite su-exec && \
    adduser -D -u 1000 appuser

COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

WORKDIR /app

COPY app/ app/
COPY *.sh *.sql ./

RUN chmod +x *.sh && chown -R appuser:appuser /app

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["./run_scrap.sh", "out"]
