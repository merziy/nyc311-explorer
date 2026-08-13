FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# $PORT is set by the hosting platform (e.g. Render) at runtime; 8000 is the local docker-compose fallback.
CMD flask --app app.main db upgrade && gunicorn --bind 0.0.0.0:${PORT:-8000} app.main:app
