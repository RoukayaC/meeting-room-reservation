#!/bin/bash
# Database backup script

# Set default values
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}
DB_USER=${DB_USER:-"postgres"}
DB_PASSWORD=${DB_PASSWORD:-"postgres"}
BACKUP_DIR=${BACKUP_DIR:-"./backups"}
USE_AWS=${USE_AWS:-"false"}
S3_BUCKET=${S3_BUCKET:-""}
RETENTION_DAYS=${RETENTION_DAYS:-"7"}

# Parse arguments
while getopts "h:p:u:P:d:a:b:r:" opt; do
  case $opt in
    h) DB_HOST="$OPTARG";;
    p) DB_PORT="$OPTARG";;
    u) DB_USER="$OPTARG";;
    P) DB_PASSWORD="$OPTARG";;
    d) DB_NAMES="$OPTARG";;
    a) USE_AWS="$OPTARG";;
    b) S3_BUCKET="$OPTARG";;
    r) RETENTION_DAYS="$OPTARG";;
    \?) echo "Invalid option -$OPTARG" >&2; exit 1;;
  esac
done

# Get databases if not provided
if [ -z "$DB_NAMES" ]; then
  echo "No databases specified, backing up all user databases"
  # Export password for psql command
  export PGPASSWORD=$DB_PASSWORD
  DB_NAMES=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "SELECT datname FROM pg_database WHERE datistemplate = false AND datname != 'postgres'" -t | tr -d ' ')
fi

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Get date for backup filename
DATE=$(date +%Y%m%d_%H%M%S)

# Backup each database
for DB in $DB_NAMES; do
  echo "Backing up database: $DB"
  BACKUP_FILE="$BACKUP_DIR/${DB}_${DATE}.sql.gz"
  
  # Export password for pg_dump
  export PGPASSWORD=$DB_PASSWORD
  
  # Dump database and compress
  pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB | gzip > $BACKUP_FILE
  
  if [ $? -eq 0 ]; then
    echo "Backup completed: $BACKUP_FILE"
    
    # Upload to S3 if AWS is enabled
    if [ "$USE_AWS" = "true" -a -n "$S3_BUCKET" ]; then
      echo "Uploading to S3 bucket: $S3_BUCKET"
      aws s3 cp $BACKUP_FILE s3://$S3_BUCKET/${DB}/
      
      if [ $? -eq 0 ]; then
        echo "Upload to S3 completed"
      else
        echo "Failed to upload to S3"
      fi
    fi
  else
    echo "Backup failed for database: $DB"
  fi
done

# Clean up old backups
if [ $RETENTION_DAYS -gt 0 ]; then
  echo "Cleaning up backups older than $RETENTION_DAYS days"
  find $BACKUP_DIR -name "*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
  
  # Clean up S3 if AWS is enabled
  if [ "$USE_AWS" = "true" -a -n "$S3_BUCKET" ]; then
    echo "Cleaning up S3 backups older than $RETENTION_DAYS days"
    # Calculate date for AWS S3 deletion
    DELETE_DATE=$(date -d "$RETENTION_DAYS days ago" +%Y-%m-%d)
    
    for DB in $DB_NAMES; do
      aws s3 ls s3://$S3_BUCKET/${DB}/ | grep -B1 $DELETE_DATE | awk '{print $4}' | xargs -I {} aws s3 rm s3://$S3_BUCKET/${DB}/{}
    done
  fi
fi

echo "Backup process completed"
