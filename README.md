# Database Backup and Restore Scripts

This directory contains scripts for backing up and restoring PostgreSQL databases.

## Backup Script (`backup_db.sh`)

Backs up PostgreSQL databases to compressed SQL files.

### Usage:
```
./backup_db.sh [-h host] [-p port] [-u username] [-P password] [-d "db1 db2..."] [-a use_aws] [-b s3_bucket] [-r retention_days]
```

### Options:
- `-h` - Database host (default: localhost)
- `-p` - Database port (default: 5432)
- `-u` - Database username (default: postgres)
- `-P` - Database password (default: postgres)
- `-d` - Space-separated list of database names (default: all user databases)
- `-a` - Use AWS S3 for storage (true/false, default: false)
- `-b` - S3 bucket name
- `-r` - Number of days to keep backups (default: 7)

## Restore Script (`restore_db.sh`)

Restores a PostgreSQL database from a backup file.

### Usage:
```
./restore_db.sh -d database_name (-f backup_file | -a true -b s3_bucket -s s3_filepath) [-h host] [-p port] [-u username] [-P password]
```

### Options:
- `-d` - Database name to restore (required)
- `-f` - Local backup file path (required if not using S3)
- `-a` - Download from AWS S3 (true/false, default: false)
- `-b` - S3 bucket name (required if using S3)
- `-s` - S3 file path (required if using S3)
- `-h` - Database host (default: localhost)
- `-p` - Database port (default: 5432)
- `-u` - Database username (default: postgres)
- `-P` - Database password (default: postgres)

## Setup Backup Cron (`setup_backup_cron.sh`)

Sets up a cron job for automated backups.

### Usage:
```
./setup_backup_cron.sh [-s schedule] [-b backup_script] [-h host] [-p port] [-u username] [-P password] [-d "db1 db2..."] [-D backup_dir] [-a use_aws] [-B s3_bucket] [-r retention_days] [-l log_file]
```

### Options:
- `-s` - Cron schedule (default: "0 2 * * *" - 2 AM daily)
- `-b` - Path to backup script (default: ./backup_db.sh)
- `-h` - Database host (default: localhost)
- `-p` - Database port (default: 5432)
- `-u` - Database username (default: postgres)
- `-P` - Database password (default: postgres)
- `-d` - Space-separated list of database names (default: all user databases)
- `-D` - Backup directory (default: ./backups)
- `-a` - Use AWS S3 for storage (true/false, default: false)
- `-B` - S3 bucket name
- `-r` - Number of days to keep backups (default: 7)
- `-l` - Log file path (default: ./backups/backup.log)
