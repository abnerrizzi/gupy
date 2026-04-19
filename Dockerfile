FROM python:3.9-alpine

RUN apk add --no-cache sqlite

WORKDIR /app

COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

COPY app/ app/
COPY *.sh *.sql ./

CMD ["/app/run_scrap.sh", "out"]