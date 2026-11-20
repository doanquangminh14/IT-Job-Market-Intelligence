# Image cho website Django. Build từ GỐC repo (cần src/, configs/ và requirements/):
#   docker compose build      hoặc      docker build -f web/Dockerfile -t itjobs-web .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # src.* import được nhờ PYTHONPATH (giữ đúng bố cục repo để src/ tìm thấy configs/ và data/)
    PYTHONPATH=/app

WORKDIR /app

# Cài thư viện trước để Docker cache lớp này khi chỉ sửa code (psycopg2-binary có sẵn wheel, không cần gcc)
COPY requirements/web.txt requirements/web.txt
RUN pip install -r requirements/web.txt

COPY src/ src/
COPY configs/ configs/
COPY web/ web/

WORKDIR /app/web
RUN python manage.py collectstatic --noinput \
    && useradd --create-home --uid 1000 app \
    && chown -R app:app /app \
    && chmod +x docker-entrypoint.sh
USER app

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
