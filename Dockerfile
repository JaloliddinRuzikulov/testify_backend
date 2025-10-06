# Python 3.12 base image
FROM python:3.12-slim

# Ish muhitini sozlash
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Ish katalogini yaratish
WORKDIR /app

# Sistema paketlarini o'rnatish (PostgreSQL client va boshqa kerakli kutubxonalar)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    python3-dev \
    musl-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Requirements fayllarini nusxalash
COPY requirements.txt .

# Python paketlarini o'rnatish
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Loyiha fayllarini nusxalash
COPY . .

# Static va media papkalarini yaratish
RUN mkdir -p /app/static /app/media

# Portni ochish
EXPOSE 8001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/api/v1/health/', timeout=5)" || exit 1

# Django serverni ishga tushirish
CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8001 --workers 4"]
