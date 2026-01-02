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

# Run database migrations if migration runner scripts exist
# The migrations are in scripts/migration/ directory with apply_migration_*.sh files
if [ -d "/app/scripts/migration" ] && [ -n "$(ls -A /app/scripts/migration/apply_migration_*.sh 2>/dev/null)" ]; then
    echo "📊 Running database migrations..."
    for migration in /app/scripts/migration/apply_migration_*.sh; do
        if [ -f "$migration" ]; then
            echo "   Running $(basename "$migration")..."
            bash "$migration" || echo "   ⚠️  Migration $(basename "$migration") failed or already applied"
        fi
    done
    echo "✅ Migrations complete"
else
    echo "ℹ️  No database migration scripts found in /app/scripts/migration/, skipping"
fi

echo "✅ Initialization complete"
echo "🎬 Starting application: $@"

# Execute the main command
exec "$@"
