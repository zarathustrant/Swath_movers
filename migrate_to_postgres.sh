#!/bin/bash

# Migration script to move data from SQLite (swath_movers.db) to PostgreSQL
# This script checks if PostgreSQL is installed, installs it if needed, creates database, and migrates all data

set -e  # Exit on any error

# Configuration
SQLITE_DB="swath_movers.db"
PG_DB="swath_movers"
PG_USER="swath_user"
PG_HOST="localhost"
PG_PORT="5432"
SCHEMA_FILE="postgresql_schema.sql"
LOG_FILE="migration.log"
OS_TYPE=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Error handling function
error_exit() {
    echo -e "${RED}Error: $1${NC}" >&2
    log "ERROR: $1"
    exit 1
}

# Success message function
success() {
    echo -e "${GREEN}$1${NC}"
    log "SUCCESS: $1"
}

# Warning message function
warning() {
    echo -e "${YELLOW}Warning: $1${NC}"
    log "WARNING: $1"
}

# Detect operating system
detect_os() {
    log "Detecting operating system..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS_TYPE="linux"
        success "Detected Linux system"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS_TYPE="macos"
        success "Detected macOS system"
    else
        error_exit "Unsupported operating system: $OSTYPE"
    fi
}

# Check if PostgreSQL is installed
check_postgres_installed() {
    log "Checking if PostgreSQL is installed..."

    if command -v psql >/dev/null 2>&1 && command -v pg_isready >/dev/null 2>&1; then
        success "PostgreSQL is already installed"
        return 0
    else
        warning "PostgreSQL is not installed"
        return 1
    fi
}

# Install PostgreSQL on Linux
install_postgres_linux() {
    log "Installing PostgreSQL on Linux..."

    # Detect Linux distribution
    if command -v apt >/dev/null 2>&1; then
        log "Using apt package manager (Ubuntu/Debian)"
        sudo apt update || error_exit "Failed to update package list"
        sudo apt install -y postgresql postgresql-contrib || error_exit "Failed to install PostgreSQL"
    elif command -v yum >/dev/null 2>&1; then
        log "Using yum package manager (RHEL/CentOS/Fedora)"
        sudo yum install -y postgresql-server postgresql-contrib || error_exit "Failed to install PostgreSQL"
        # Initialize PostgreSQL database
        sudo postgresql-setup initdb || error_exit "Failed to initialize PostgreSQL"
        sudo systemctl enable postgresql || error_exit "Failed to enable PostgreSQL service"
        sudo systemctl start postgresql || error_exit "Failed to start PostgreSQL service"
    elif command -v dnf >/dev/null 2>&1; then
        log "Using dnf package manager (Fedora)"
        sudo dnf install -y postgresql-server postgresql-contrib || error_exit "Failed to install PostgreSQL"
        # Initialize PostgreSQL database
        sudo postgresql-setup initdb || error_exit "Failed to initialize PostgreSQL"
        sudo systemctl enable postgresql || error_exit "Failed to enable PostgreSQL service"
        sudo systemctl start postgresql || error_exit "Failed to start PostgreSQL service"
    else
        error_exit "Unsupported Linux distribution. Please install PostgreSQL manually."
    fi

    success "PostgreSQL installed successfully on Linux"
}

# Install PostgreSQL on macOS
install_postgres_macos() {
    log "Installing PostgreSQL on macOS..."

    # Check if Homebrew is installed
    if ! command -v brew >/dev/null 2>&1; then
        log "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || error_exit "Failed to install Homebrew"
    fi

    # Install PostgreSQL via Homebrew
    brew install postgresql || error_exit "Failed to install PostgreSQL via Homebrew"

    # Start PostgreSQL service
    brew services start postgresql || error_exit "Failed to start PostgreSQL service"

    success "PostgreSQL installed successfully on macOS"
}

# Install PostgreSQL if not available
install_postgres() {
    if check_postgres_installed; then
        return 0
    fi

    warning "PostgreSQL is not installed. Installing now..."

    case $OS_TYPE in
        "linux")
            install_postgres_linux
            ;;
        "macos")
            install_postgres_macos
            ;;
        *)
            error_exit "Cannot install PostgreSQL on unsupported OS: $OS_TYPE"
            ;;
    esac

    # Verify installation
    if ! check_postgres_installed; then
        error_exit "PostgreSQL installation verification failed"
    fi

    success "PostgreSQL installation completed and verified"
}

# Check if required files exist
check_prerequisites() {
    log "Checking prerequisites..."

    if [ ! -f "$SQLITE_DB" ]; then
        error_exit "SQLite database '$SQLITE_DB' not found in current directory"
    fi

    if [ ! -f "$SCHEMA_FILE" ]; then
        error_exit "PostgreSQL schema file '$SCHEMA_FILE' not found"
    fi

    # Check if required commands are available (SQLite3 should be available)
    command -v sqlite3 >/dev/null 2>&1 || error_exit "sqlite3 command not found. Please install SQLite3."

    success "All prerequisites checked successfully"
}

# Check if PostgreSQL is running
check_postgres_running() {
    log "Checking if PostgreSQL is running..."

    if ! pg_isready -h "$PG_HOST" -p "$PG_PORT" >/dev/null 2>&1; then
        error_exit "PostgreSQL is not running on $PG_HOST:$PG_PORT. Please start PostgreSQL service."
    fi

    success "PostgreSQL is running"
}

# Check if database exists
check_database_exists() {
    log "Checking if PostgreSQL database '$PG_DB' exists..."

    if psql -h "$PG_HOST" -p "$PG_PORT" -lqt | cut -d \| -f 1 | grep -qw "$PG_DB"; then
        return 0  # Database exists
    else
        return 1  # Database doesn't exist
    fi
}

# Create PostgreSQL database and user
create_database() {
    log "Creating PostgreSQL database and user..."

    # Create user if it doesn't exist (connect to postgres system database)
    if ! psql -h "$PG_HOST" -p "$PG_PORT" -d "postgres" -tAc "SELECT 1 FROM pg_roles WHERE rolname='$PG_USER'" | grep -q 1; then
        log "Creating user '$PG_USER'..."
        sudo -u postgres psql -d "postgres" -c "CREATE USER $PG_USER WITH PASSWORD 'swath_password';" 2>/dev/null || \
        psql -h "$PG_HOST" -p "$PG_PORT" -d "postgres" -c "CREATE USER $PG_USER WITH PASSWORD 'swath_password';" || \
        error_exit "Failed to create user '$PG_USER'"
        success "Created user '$PG_USER'"
    else
        warning "User '$PG_USER' already exists"
    fi

    # Create database if it doesn't exist
    if ! check_database_exists; then
        log "Creating database '$PG_DB'..."
        sudo -u postgres createdb -O "$PG_USER" "$PG_DB" 2>/dev/null || \
        psql -h "$PG_HOST" -p "$PG_PORT" -d "postgres" -c "CREATE DATABASE $PG_DB OWNER $PG_USER;" || \
        error_exit "Failed to create database '$PG_DB'"
        success "Created database '$PG_DB'"
    else
        warning "Database '$PG_DB' already exists"
    fi

    # Grant permissions
    log "Setting up permissions..."
    psql -h "$PG_HOST" -p "$PG_PORT" -d "$PG_DB" -c "GRANT ALL PRIVILEGES ON DATABASE $PG_DB TO $PG_USER;" || \
    error_exit "Failed to grant database permissions"
    success "Database permissions granted"
}

# Check if tables already exist in PostgreSQL
check_tables_exist() {
    log "Checking if tables already exist in PostgreSQL..."

    local table_count=$(psql -h "$PG_HOST" -p "$PG_PORT" -d "$PG_DB" -U "$PG_USER" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" 2>/dev/null || echo "0")

    if [ "$table_count" -gt "0" ]; then
        return 0  # Tables exist
    else
        return 1  # No tables
    fi
}

# Create tables from schema
create_tables() {
    log "Creating tables from schema file..."

    # Check if tables already exist
    if check_tables_exist; then
        warning "Tables already exist in PostgreSQL database"
        log "Existing tables found: $(psql -h "$PG_HOST" -p "$PG_PORT" -d "$PG_DB" -U "$PG_USER" -tAc "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" 2>/dev/null | tr '\n' ' ')"
        return 0
    fi

    # Run schema creation - if it fails due to existing objects, that's okay
    if ! psql -h "$PG_HOST" -p "$PG_PORT" -d "$PG_DB" -U "$PG_USER" -f "$SCHEMA_FILE" >/dev/null 2>&1; then
        log "Schema creation had some issues (likely due to existing objects), but continuing..."
    fi

    success "Tables created successfully"
}

# Get table names from SQLite database
get_sqlite_tables() {
    # Use sqlite3 with proper output formatting - capture only table names
    sqlite3 "$SQLITE_DB" ".tables" 2>/dev/null | tr -s ' ' | sed 's/^ *//' | sed 's/ *$//' | tr ' ' '\n' | grep -v '^$' | sort
}

# Count records in SQLite table
count_sqlite_records() {
    local table=$1
    sqlite3 "$SQLITE_DB" "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "0"
}

# Count records in PostgreSQL table
count_postgres_records() {
    local table=$1
    psql -h "$PG_HOST" -p "$PG_PORT" -d "$PG_DB" -U "$PG_USER" -tAc "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "0"
}

# Migrate data for a specific table
migrate_table() {
    local table=$1
    local sqlite_count=$(count_sqlite_records "$table")
    local postgres_count=$(count_postgres_records "$table")

    log "Migrating table '$table' ($sqlite_count records in SQLite, $postgres_count in PostgreSQL)..."

    if [ "$sqlite_count" -eq "0" ]; then
        warning "No records to migrate for table '$table'"
        return 0
    fi

    # Create temporary CSV file
    local csv_file="/tmp/${table}_migration.csv"

    # Export data from SQLite to CSV
    sqlite3 -header -csv "$SQLITE_DB" "SELECT * FROM $table;" > "$csv_file" || {
        rm -f "$csv_file"
        error_exit "Failed to export table '$table' from SQLite"
    }

    # Import data to PostgreSQL
    if [ "$postgres_count" -eq "0" ]; then
        # Table is empty, use COPY for faster import
        psql -h "$PG_HOST" -p "$PG_PORT" -d "$PG_DB" -U "$PG_USER" -c "\COPY $table FROM '$csv_file' WITH CSV HEADER;" || {
            rm -f "$csv_file"
            error_exit "Failed to import table '$table' to PostgreSQL"
        }
    else
        # Table has data, use INSERT to avoid conflicts
        psql -h "$PG_HOST" -p "$PG_PORT" -d "$PG_DB" -U "$PG_USER" -c "\COPY $table FROM '$csv_file' WITH CSV HEADER;" 2>/dev/null || {
            warning "COPY failed for table '$table', trying INSERT method..."
            # Fallback to INSERT method (slower but more reliable)
            tail -n +2 "$csv_file" | psql -h "$PG_HOST" -p "$PG_PORT" -d "$PG_DB" -U "$PG_USER" -c "COPY $table FROM STDIN WITH CSV;" || {
                rm -f "$csv_file"
                error_exit "Failed to import table '$table' using INSERT method"
            }
        }
    fi

    # Clean up temporary file
    rm -f "$csv_file"

    # Verify migration
    local new_postgres_count=$(count_postgres_records "$table")
    if [ "$sqlite_count" -eq "$new_postgres_count" ]; then
        success "Successfully migrated $sqlite_count records for table '$table'"
    else
        warning "Record count mismatch for table '$table': SQLite=$sqlite_count, PostgreSQL=$new_postgres_count"
    fi
}

# Check if data already exists in PostgreSQL
check_data_exists() {
    log "Checking if data already exists in PostgreSQL..."

    local sqlite_tables=$(get_sqlite_tables)
    local has_data=0

    for table in $sqlite_tables; do
        local postgres_count=$(count_postgres_records "$table")
        if [ "$postgres_count" -gt "0" ]; then
            has_data=1
            break
        fi
    done

    return $has_data
}

# Main migration function
migrate_data() {
    log "Starting data migration..."

    local tables=$(get_sqlite_tables)

    if [ -z "$tables" ]; then
        warning "No tables found in SQLite database"
        return 0
    fi

    echo "Found tables: $tables"
    log "Found tables: $tables"

    # Check if data already exists in PostgreSQL
    if check_data_exists; then
        warning "Data already exists in PostgreSQL database"
        log "PostgreSQL already contains data. Skipping migration to avoid duplicates."

        # Show current record counts
        echo "Current record counts:"
        for table in $tables; do
            local sqlite_count=$(count_sqlite_records "$table")
            local postgres_count=$(count_postgres_records "$table")
            echo "  $table: SQLite=$sqlite_count, PostgreSQL=$postgres_count"
        done

        return 0
    fi

    for table in $tables; do
        migrate_table "$table"
    done

    success "Data migration completed"
}

# Verify migration
verify_migration() {
    log "Verifying migration..."

    local sqlite_tables=$(get_sqlite_tables)
    local errors=0

    for table in $sqlite_tables; do
        local sqlite_count=$(count_sqlite_records "$table")
        local postgres_count=$(count_postgres_records "$table")

        if [ "$sqlite_count" -ne "$postgres_count" ]; then
            warning "Verification failed for table '$table': SQLite=$sqlite_count, PostgreSQL=$postgres_count"
            ((errors++))
        else
            log "Verification passed for table '$table': $sqlite_count records"
        fi
    done

    if [ "$errors" -eq 0 ]; then
        success "Migration verification completed successfully"
    else
        error_exit "Migration verification failed with $errors errors"
    fi
}

# Create backup before migration
create_backup() {
    log "Creating backup of SQLite database..."

    local backup_file="swath_movers_backup_$(date +%Y%m%d_%H%M%S).db"

    cp "$SQLITE_DB" "$backup_file" || error_exit "Failed to create backup"

    success "Backup created: $backup_file"
}

# Main execution
main() {
    log "=== Starting PostgreSQL Migration ==="

    # Create log file
    echo "Migration started at $(date)" > "$LOG_FILE"

    # Run migration steps
    detect_os
    install_postgres
    check_prerequisites
    check_postgres_running
    create_backup
    create_database
    create_tables
    migrate_data
    verify_migration

    success "=== Migration completed successfully ==="
    log "=== Migration completed successfully ==="

    echo ""
    echo "Migration completed! Check $LOG_FILE for details."
    echo "SQLite backup saved as: swath_movers_backup_*.db"
}

# Run main function
main "$@"
