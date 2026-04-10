FROM python:3.9-alpine

RUN apk add sqlite

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/app.py .

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]