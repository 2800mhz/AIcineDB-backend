#!/bin/bash
set -e

echo "Starting AIcineDB Backend..."

# Function to wait for a service to be ready
wait_for_service() {
    local service_name=$1
    local host=$2
    local port=$3
    
    echo "Waiting for $service_name at $host:$port..."
    
    max_attempts=30
    attempt=0
    
    until nc -z "$host" "$port" 2>/dev/null || [ $attempt -eq $max_attempts ]; do
        echo "$service_name is unavailable - sleeping (attempt $((attempt+1))/$max_attempts)"
        sleep 2
        attempt=$((attempt+1))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo "ERROR: $service_name did not become available in time"
        exit 1
    fi
    
    echo "$service_name is up!"
}

# Wait for PostgreSQL to be ready
if [ -n "$DATABASE_HOST" ]; then
    wait_for_service "PostgreSQL" "$DATABASE_HOST" "${DATABASE_PORT:-5432}"
fi

# Wait for Redis to be ready
if [ -n "$REDIS_HOST" ]; then
    wait_for_service "Redis" "$REDIS_HOST" "${REDIS_PORT:-6379}"
fi

# Start the application
echo "Starting application..."
exec "$@"
