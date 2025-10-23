# PostgreSQL Migration Script

This script migrates data from the SQLite database (`swath_movers.db`) to PostgreSQL. It **automatically detects your operating system, installs PostgreSQL if needed**, creates the database, and migrates all data with proper error handling and verification.

## Features

- **🔄 Automatic PostgreSQL installation**: Detects OS (Linux/macOS) and installs PostgreSQL automatically
- **🗄️ Automatic database setup**: Creates database and user if they don't exist
- **📋 Schema creation**: Creates all necessary tables from `postgresql_schema.sql`
- **📊 Data migration**: Migrates all data from SQLite to PostgreSQL using efficient CSV import
- **💾 Backup creation**: Creates timestamped backups of the SQLite database before migration
- **🚫 Duplicate prevention**: Detects existing data and skips migration to avoid duplicates
- **✅ Verification**: Verifies that all data was migrated correctly
- **📝 Comprehensive logging**: Logs all operations to `migration.log`

## Prerequisites

1. **SQLite database** (`swath_movers.db`) must exist in the current directory
2. **Schema file** (`postgresql_schema.sql`) must exist in the current directory
3. **Required commands**: `sqlite3` (usually pre-installed)
4. **Internet connection** (for downloading PostgreSQL if not installed)
5. **Administrative privileges** (sudo access for PostgreSQL installation)

**Note**: The script will automatically install PostgreSQL if it's not already available!

## Usage

### Basic Usage

```bash
# Make sure you're in the swath-movers directory
cd swath-movers

# Run the migration script
./migrate_to_postgres.sh
```

### What the script does

1. **OS Detection**: Automatically detects if you're running Linux or macOS
2. **PostgreSQL Installation**: Installs PostgreSQL automatically if not already available
3. **Prerequisites check**: Verifies all required files and commands are available
4. **PostgreSQL check**: Ensures PostgreSQL is running
5. **Backup creation**: Creates a timestamped backup of the SQLite database
6. **Database setup**: Creates PostgreSQL database and user if they don't exist
7. **Schema creation**: Creates tables from the schema file (skips if tables already exist)
8. **Data migration**: Migrates all data from SQLite to PostgreSQL
9. **Verification**: Verifies that all data was migrated correctly

### Configuration

The script uses these default settings (configurable at the top of the script):

```bash
SQLITE_DB="swath_movers.db"      # Source SQLite database
PG_DB="swath_movers"             # Target PostgreSQL database
PG_USER="swath_user"             # PostgreSQL user to create
PG_HOST="localhost"              # PostgreSQL host
PG_PORT="5432"                   # PostgreSQL port
SCHEMA_FILE="postgresql_schema.sql"  # Schema file to use
LOG_FILE="migration.log"         # Log file location
```

## Output

The script provides colored output:
- **Green**: Success messages
- **Yellow**: Warnings (non-critical issues)
- **Red**: Errors (critical failures)

### Example Output

```
2025-10-23 19:04:01 - === Starting PostgreSQL Migration ===
2025-10-23 19:04:01 - Checking prerequisites...
All prerequisites checked successfully
2025-10-23 19:04:01 - SUCCESS: All prerequisites checked successfully
2025-10-23 19:04:01 - Checking if PostgreSQL is running...
PostgreSQL is running
2025-10-23 19:04:01 - SUCCESS: PostgreSQL is running
2025-10-23 19:04:01 - Creating backup of SQLite database...
Backup created: swath_movers_backup_20251023_190401.db
2025-10-23 19:04:01 - SUCCESS: Backup created: swath_movers_backup_20251023_190401.db
Warning: Database 'swath_movers' already exists
Warning: Tables already exist in PostgreSQL database
Warning: Data already exists in PostgreSQL database
PostgreSQL already contains data. Skipping migration to avoid duplicates.
=== Migration completed successfully ===
```

## Files Created/Modified

- **Backup file**: `swath_movers_backup_YYYYMMDD_HHMMSS.db` (SQLite backup)
- **Log file**: `migration.log` (detailed operation log)

## Automatic PostgreSQL Installation

The script automatically detects your operating system and installs PostgreSQL if it's not already available:

### Linux Installation
- **Ubuntu/Debian**: Uses `apt` package manager
- **RHEL/CentOS/Fedora**: Uses `yum` or `dnf` package managers
- **Systemd services**: Automatically enables and starts PostgreSQL service

### macOS Installation
- **Homebrew**: Installs Homebrew if not available
- **PostgreSQL**: Installs via Homebrew package manager
- **Services**: Automatically starts PostgreSQL service

### Installation Requirements
- **Internet connection** for downloading packages
- **Administrative privileges** (sudo access)
- **Compatible system**: Linux (Ubuntu, Debian, RHEL, CentOS, Fedora) or macOS

## Troubleshooting

### Installation Issues

1. **Installation fails on Linux**
   ```bash
   # Update package manager
   sudo apt update  # Ubuntu/Debian
   sudo yum update  # RHEL/CentOS
   sudo dnf update  # Fedora
   ```

2. **Permission denied during installation**
   ```bash
   # Ensure you have sudo access
   sudo -l
   ```

3. **Homebrew installation fails on macOS**
   ```bash
   # Install Xcode command line tools first
   xcode-select --install
   ```

### Common Issues

1. **PostgreSQL not running**
   ```bash
   # Start PostgreSQL service
   sudo service postgresql start
   # or on macOS
   brew services start postgresql
   ```

2. **Permission denied errors**
   ```bash
   # Make sure the script is executable
   chmod +x migrate_to_postgres.sh
   ```

3. **Database connection errors**
   - Ensure PostgreSQL is running on localhost:5432
   - Check if the database/user already exists with different permissions
   - Verify PostgreSQL accepts local connections

4. **Missing files**
   - Ensure `swath_movers.db` exists in the current directory
   - Ensure `postgresql_schema.sql` exists in the current directory

### Log Analysis

Check the `migration.log` file for detailed error messages:

```bash
tail -f migration.log  # Monitor live
cat migration.log      # View complete log
```

## Re-running the Migration

The script is designed to be safe to re-run:

- **Database creation**: Skipped if database already exists
- **Table creation**: Skipped if tables already exist
- **Data migration**: Skipped if data already exists in PostgreSQL
- **Backup creation**: Always creates a new backup

## Manual Operations

If you need to perform manual operations:

```bash
# Check PostgreSQL status
pg_isready -h localhost -p 5432

# List PostgreSQL databases
psql -l

# Connect to the migrated database
psql -h localhost -p 5432 -d swath_movers -U swath_user

# Check table record counts
psql -h localhost -p 5432 -d swath_movers -U swath_user -c "SELECT schemaname, tablename, n_tup_ins - n_tup_del as records FROM pg_stat_user_tables ORDER BY records DESC;"
```

## Security Notes

- The script creates a PostgreSQL user with the password `swath_password`
- Consider changing this password after migration for production use
- The script requires appropriate permissions to create databases and users

## Integration with Application

After successful migration:

1. Update your application configuration to use PostgreSQL instead of SQLite
2. Update connection strings in your application code
3. Test the application thoroughly with the new database
4. Consider keeping the SQLite backup for rollback purposes

## Support

If you encounter issues:

1. Check the `migration.log` file for detailed error messages
2. Verify all prerequisites are met
3. Ensure PostgreSQL is properly configured and running
4. Check file permissions and paths
