#!/bin/bash
set -e

echo "Starting AIcineDB Backend..."

# Wait for database to be ready
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database to be ready..."
    while ! nc -z $(echo $DATABASE_URL | sed 's/.*@\([^:]*\).*/\1/') $(echo $DATABASE_URL | sed 's/.*:\([0-9]*\).*/\1/') 2>/dev/null; do
        echo "Database is unavailable - sleeping"
        sleep 1
    done
    echo "Database is up!"
fi

# Run migrations if needed
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running database migrations..."
    python manage.py migrate
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the application
echo "Starting gunicorn server..."
exec "$@"
