FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY . .


CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn theatre_booking.wsgi:application --bind 0.0.0.0:8000"]
