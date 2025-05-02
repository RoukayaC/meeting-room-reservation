#!/bin/bash
# Database restore script

# Set default values
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}
DB_USER=${DB_USER:-"postgres"}
DB_PASSWORD=${DB_PASSWORD:-"postgres"}
DB_NAME=""
BACKUP_FILE=""
FROM_AWS=${FROM_AWS:-"false"}
S3_BUCKET=${S3_BUCKET:-""}
S3_FILE_PATH=""

# Parse arguments
while getopts "h:p:u:P:d:f:a:b:s:" opt; do
  case $opt in
    h) DB_HOST="$OPTARG";;
    p) DB_PORT="$OPTARG";;
    u) DB_USER="$OPTARG";;
    P) DB_PASSWORD="$OPTARG";;
    d) DB_NAME="$OPTARG";;
    f) BACKUP_FILE="$OPTARG";;
    a) FROM_AWS="$OPTARG";;
    b) S3_BUCKET="$OPTARG";;
    s) S3_FILE_PATH="$OPTARG";;
    \?) echo "Invalid option -$OPTARG" >&2; exit 1;;
  esac
done

# Check required parameters
if [ -z "$DB_NAME" ]; then
  echo "Error: Database name is required (-d)"
  exit 1
fi

# From AWS or local file
if [ "$FROM_AWS" = "true" ]; then
  if [ -z "$S3_BUCKET" -o -z "$S3_FILE_PATH" ]; then
    echo "Error: S3 bucket and file path are required (-b and -s)"
    exit 1
  fi
  
  # Download from S3
  echo "Downloading backup from S3: s3://$S3_BUCKET/$S3_FILE_PATH"
  aws s3 cp s3://$S3_BUCKET/$S3_FILE_PATH /tmp/restore_temp.sql.gz
  
  if [ $? -ne 0 ]; then
    echo "Error: Failed to download from S3"
    exit 1
  fi
  
  BACKUP_FILE="/tmp/restore_temp.sql.gz"
elif [ -z "$BACKUP_FILE" ]; then
  echo "Error: Backup file is required (-f)"
  exit 1
fi

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: Backup file does not exist: $BACKUP_FILE"
  exit 1
fi

echo "Restoring database $DB_NAME from $BACKUP_FILE"

# Export password for psql command
export PGPASSWORD=$DB_PASSWORD

# First, check if database exists
DB_EXISTS=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")

# Create database if it doesn't exist
if [ -z "$DB_EXISTS" ]; then
  echo "Creating database $DB_NAME"
  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE DATABASE $DB_NAME"
else
  echo "Database $DB_NAME already exists. Dropping all tables before restore."
  # Drop all tables first
  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
    DO \$\$ 
    DECLARE
      r RECORD;
    BEGIN
      FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
      END LOOP;
    END \$\$;
  "
fi

# Restore database
echo "Restoring data..."
gunzip -c $BACKUP_FILE | psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME

if [ $? -eq 0 ]; then
  echo "Restore completed successfully!"
else
  echo "Error: Restore failed"
  exit 1
fi

# Clean up temporary file if downloaded from S3
if [ "$FROM_AWS" = "true" ]; then
  rm -f /tmp/restore_temp.sql.gz
fi
