#!/bin/sh
# Áp migration rồi chạy lệnh CMD (gunicorn). docker compose chỉ khởi động web khi PostgreSQL đã sẵn sàng (healthcheck).
set -e

python manage.py migrate --noinput

exec "$@"
