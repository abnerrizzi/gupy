FROM python:3.12-alpine

COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

RUN apk add --no-cache sqlite 

WORKDIR /app

COPY app/ app/
COPY *.sh *.sql ./

RUN chmod +x *.sh

CMD ["./run_scrap.sh", "out"]
