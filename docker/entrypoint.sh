#!/bin/bash
set -e

echo "🚀 Starting AIcineDB Backend Service..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
until pg_isready -h "${DATABASE_HOST:-postgres}" -p "${DATABASE_PORT:-5432}" -U "${DATABASE_USER:-aicine_user}" 2>/dev/null; do
    echo "   PostgreSQL is unavailable - sleeping"
    sleep 2
done
echo "✅ PostgreSQL is up"

# Wait for Redis to be ready
echo "⏳ Waiting for Redis..."
until redis-cli -h "${REDIS_HOST:-redis}" -p "${REDIS_PORT:-6379}" ping 2>/dev/null; do
    echo "   Redis is unavailable - sleeping"
    sleep 2
done
echo "✅ Redis is up"

# Run database migrations if they exist
if [ -d "/app/backend/database/migrations" ]; then
    echo "📊 Running database migrations..."
    # Check if there's a migration runner script, otherwise skip
    if [ -f "/app/scripts/run_migrations.sh" ]; then
        bash /app/scripts/run_migrations.sh
    else
        echo "   No migration script found, skipping migrations"
    fi
fi

echo "✅ Initialization complete"
echo "🎬 Starting application: $@"

# Execute the main command
exec "$@"
