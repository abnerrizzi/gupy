# Use the official Python image from the Docker Hub
FROM python:3.9-alpine

RUN apk add sqlite

WORKDIR /app

COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

COPY app/* app/
COPY *.sh *.sql .

ENTRYPOINT ["/bin/sh"]
