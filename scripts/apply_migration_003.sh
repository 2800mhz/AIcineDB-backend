#!/bin/bash
# Script to apply database migration: Add user_id to analysis_jobs table

# This script applies migration 003_add_user_id_to_analysis_jobs.sql
# Run this if you have an existing database and need to add the user_id column

# Default database connection (can be overridden with environment variables)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-aicine}"
DB_USER="${DB_USER:-aicine_user}"

echo "🔄 Applying migration: 003_add_user_id_to_analysis_jobs"
echo "📊 Database: $DB_NAME on $DB_HOST:$DB_PORT"
echo ""

# Check if migration file exists
MIGRATION_FILE="backend/database/migrations/003_add_user_id_to_analysis_jobs.sql"

if [ ! -f "$MIGRATION_FILE" ]; then
    echo "❌ Migration file not found: $MIGRATION_FILE"
    exit 1
fi

# Apply migration
echo "Applying migration..."
PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration applied successfully!"
    echo ""
    echo "Verifying column was added..."
    PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\d analysis_jobs" | grep "user_id"
    if [ $? -eq 0 ]; then
        echo "✅ Verified: user_id column exists in analysis_jobs table"
    else
        echo "⚠️  Warning: Could not verify column (but migration may have succeeded)"
    fi
else
    echo "❌ Migration failed"
    exit 1
fi
