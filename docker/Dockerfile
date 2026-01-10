FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY ../requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY .. /app

ENV FLASK_ENV=production \
    FLASK_APP=run.py \
    FLASK_PORT=5003

EXPOSE 5003

CMD ["gunicorn", "-b", "0.0.0.0:5003", "run:app"]
