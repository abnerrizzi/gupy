FROM python:3.9-alpine

WORKDIR /app

COPY app/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt && rm /tmp/req.txt

RUN apk add sqlite
CMD ["sh"]
