#!/bin/bash
set -e

echo "Starting AIcineDB Backend..."

# Wait for PostgreSQL to be ready
if [ -n "$DATABASE_HOST" ]; then
    echo "Waiting for PostgreSQL at $DATABASE_HOST:${DATABASE_PORT:-5432}..."
    
    max_attempts=30
    attempt=0
    
    until nc -z "$DATABASE_HOST" "${DATABASE_PORT:-5432}" 2>/dev/null || [ $attempt -eq $max_attempts ]; do
        echo "PostgreSQL is unavailable - sleeping (attempt $((attempt+1))/$max_attempts)"
        sleep 2
        attempt=$((attempt+1))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo "ERROR: PostgreSQL did not become available in time"
        exit 1
    fi
    
    echo "PostgreSQL is up!"
fi

# Wait for Redis to be ready
if [ -n "$REDIS_HOST" ]; then
    echo "Waiting for Redis at $REDIS_HOST:${REDIS_PORT:-6379}..."
    
    max_attempts=30
    attempt=0
    
    until nc -z "$REDIS_HOST" "${REDIS_PORT:-6379}" 2>/dev/null || [ $attempt -eq $max_attempts ]; do
        echo "Redis is unavailable - sleeping (attempt $((attempt+1))/$max_attempts)"
        sleep 2
        attempt=$((attempt+1))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo "ERROR: Redis did not become available in time"
        exit 1
    fi
    
    echo "Redis is up!"
fi

# Start the application
echo "Starting application..."
exec "$@"
