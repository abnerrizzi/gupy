FROM python:3.12-alpine

RUN apk add --no-cache sqlite su-exec

WORKDIR /app

COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

COPY app/ app/
COPY *.sh *.sql ./

RUN chmod +x *.sh

ENTRYPOINT ["./docker-entrypoint.sh"]

CMD ["./run_scrap.sh", "out"]