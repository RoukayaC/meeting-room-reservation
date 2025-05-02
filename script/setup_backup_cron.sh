#!/bin/bash
# Script to set up automatic database backups using cron

# Default values
SCHEDULE=${SCHEDULE:-"0 2 * * *"}  # 2 AM daily
BACKUP_SCRIPT=${BACKUP_SCRIPT:-"$(pwd)/backup_db.sh"}
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}
DB_USER=${DB_USER:-"postgres"}
DB_PASSWORD=${DB_PASSWORD:-"postgres"}
DB_NAMES=${DB_NAMES:-""}
BACKUP_DIR=${BACKUP_DIR:-"$(pwd)/backups"}
USE_AWS=${USE_AWS:-"false"}
S3_BUCKET=${S3_BUCKET:-""}
RETENTION_DAYS=${RETENTION_DAYS:-"7"}
LOG_FILE=${LOG_FILE:-"$(pwd)/backups/backup.log"}

# Parse arguments
while getopts "s:b:h:p:u:P:d:D:a:B:r:l:" opt; do
  case $opt in
    s) SCHEDULE="$OPTARG";;
    b) BACKUP_SCRIPT="$OPTARG";;
    h) DB_HOST="$OPTARG";;
    p) DB_PORT="$OPTARG";;
    u) DB_USER="$OPTARG";;
    P) DB_PASSWORD="$OPTARG";;
    d) DB_NAMES="$OPTARG";;
    D) BACKUP_DIR="$OPTARG";;
    a) USE_AWS="$OPTARG";;
    B) S3_BUCKET="$OPTARG";;
    r) RETENTION_DAYS="$OPTARG";;
    l) LOG_FILE="$OPTARG";;
    \?) echo "Invalid option -$OPTARG" >&2; exit 1;;
  esac
done

# Ensure backup directory exists
mkdir -p $(dirname "$LOG_FILE")

# Create backup command
DB_OPTIONS=""
if [ -n "$DB_NAMES" ]; then
  DB_OPTIONS="-d \"$DB_NAMES\""
fi

AWS_OPTIONS=""
if [ "$USE_AWS" = "true" -a -n "$S3_BUCKET" ]; then
  AWS_OPTIONS="-a true -b \"$S3_BUCKET\""
fi

BACKUP_CMD="$BACKUP_SCRIPT -h \"$DB_HOST\" -p \"$DB_PORT\" -u \"$DB_USER\" -P \"$DB_PASSWORD\" $DB_OPTIONS -r \"$RETENTION_DAYS\" $AWS_OPTIONS >> \"$LOG_FILE\" 2>&1"

# Create temporary file for crontab
TEMP_CRON=$(mktemp)
crontab -l > "$TEMP_CRON" 2>/dev/null

# Remove any existing backup job
grep -v "$BACKUP_SCRIPT" "$TEMP_CRON" > "${TEMP_CRON}.new"
mv "${TEMP_CRON}.new" "$TEMP_CRON"

# Add new backup job
echo "# Database backup job" >> "$TEMP_CRON"
echo "$SCHEDULE $BACKUP_CMD" >> "$TEMP_CRON"

# Install new crontab
crontab "$TEMP_CRON"
rm "$TEMP_CRON"

echo "Backup cron job installed:"
echo "Schedule: $SCHEDULE"
echo "Command: $BACKUP_CMD"
echo "Log file: $LOG_FILE"
