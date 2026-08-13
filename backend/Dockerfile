FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# see CLAUDE.md, "Deployment"
CMD flask --app app.main db upgrade && gunicorn --bind 0.0.0.0:${PORT:-8000} app.main:app
