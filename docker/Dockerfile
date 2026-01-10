FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY . /app

ENV FLASK_ENV=production \
    FLASK_APP=run.py

EXPOSE 5003

# Gunicorn with proper worker configuration
# Workers = 2 * CPU cores + 1 (default 3 for small server)
CMD ["gunicorn", "--bind", "0.0.0.0:5003", "--workers", "3", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "run:app"]
