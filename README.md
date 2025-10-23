# Swath Movers - PostgreSQL Migration

This document outlines the migration from SQLite to PostgreSQL and the improvements made to the database infrastructure.

## 🚀 Migration Summary

The application has been successfully migrated from SQLite to PostgreSQL with the following improvements:

### ✅ Completed Tasks
- [x] Remove SQLite dependencies
- [x] Add comprehensive PostgreSQL error handling
- [x] Update backup and recovery procedures
- [x] Configure PostgreSQL for production use
- [x] Create database operation tests
- [x] Update deployment scripts

## 📋 Prerequisites

### PostgreSQL Installation
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql-server postgresql-contrib
```

### Database Setup
```bash
# Start PostgreSQL service
sudo service postgresql start

# Create database and user
sudo -u postgres createuser --superuser oluseyioyetunde
sudo -u postgres createdb swath_movers
```

## 🗄️ Database Schema

The PostgreSQL schema includes:

- **coordinates**: Base shotpoint data with spatial indexing
- **users**: User authentication with password hashing
- **global_deployments**: Centralized deployment tracking
- **swath_1 through swath_8**: Individual swath deployment tables
- **swath_lines**: Performance cache for map lines
- **swath_boxes**: Performance cache for bounding boxes

### Schema File
See `postgresql_schema.sql` for the complete database schema with indexes and constraints.

## 🔧 Configuration

### Database Connection
The application uses connection pooling for better performance:

```python
DB_CONFIG = {
    'dbname': 'swath_movers',
    'user': 'oluseyioyetunde',
    'password': '',
    'host': 'localhost',
    'port': '5432'
}
```

### Production Configuration
- **Connection Pool**: 1-10 connections
- **SSL**: Enabled for production
- **Logging**: DDL statements and slow queries
- **Autovacuum**: Optimized for performance

## 🛠️ Backup and Recovery

### Automated Backups
- **Daily backups**: Run at 2 AM via cron
- **Retention**: 30 days of backups
- **Format**: SQL dumps using pg_dump

### Backup Scripts
```bash
# Create backup
./backup_db.sh

# Restore from backup
./restore_db.sh

# Pull backup from VM
./backup_from_vm.sh
```

### Manual Backup
```bash
pg_dump -h localhost -U oluseyioyetunde -d swath_movers -f backup.sql
```

## 🧪 Testing

### Database Tests
Run comprehensive tests to verify database operations:

```bash
python test_database.py
```

Tests include:
- Database connection
- Table initialization
- Coordinate lookup
- Global deployments
- Data migration

## 🚀 Deployment

### VM Deployment
```bash
# Deploy to VM
./deploy.sh

# Manual deployment steps
gcloud compute ssh discord-bot-vm --zone=us-central1-a
cd ~/swath-movers
source swathenv/bin/activate
pip install -r requirements.txt
python app.py  # Run migrations
gunicorn -b 0.0.0.0:8080 -w 4 app:app
```

### Environment Variables
For production, set these environment variables:
```bash
export DB_HOST=your-postgres-host
export DB_PASSWORD=your-secure-password
export DB_SSLMODE=require
```

## 🔒 Security Improvements

### PostgreSQL Security
- SSL connections enabled
- Parameterized queries (prevents SQL injection)
- Connection pooling for resource management
- Proper error handling without exposing sensitive data

### Authentication
- Password hashing with werkzeug.security
- Session management
- User permissions system

## 📊 Performance Improvements

### Database Performance
- **Connection Pooling**: Reduces connection overhead
- **Indexes**: Optimized queries on frequently accessed columns
- **Caching**: Line and box data cached for map performance
- **Batch Operations**: Efficient bulk inserts and updates

### Application Performance
- **Error Handling**: Graceful degradation on database errors
- **Connection Management**: Proper connection lifecycle
- **Query Optimization**: Efficient PostgreSQL queries

## 🔄 Migration Process

### From SQLite to PostgreSQL
1. **Schema Migration**: Convert SQLite schema to PostgreSQL
2. **Data Migration**: Transfer all existing data
3. **Code Updates**: Replace SQLite calls with PostgreSQL
4. **Testing**: Verify all operations work correctly
5. **Deployment**: Update production environment

### Rollback Plan
If needed, you can restore from SQL backups:
```bash
./restore_db.sh
```

## 📝 Files Modified

### Core Application
- `app.py`: Main application with PostgreSQL integration
- `requirements.txt`: Updated dependencies
- `postgresql_schema.sql`: Database schema

### Backup & Recovery
- `backup_db.sh`: PostgreSQL backup script
- `restore_db.sh`: PostgreSQL restore script
- `backup_from_vm.sh`: VM backup synchronization

### Configuration & Testing
- `postgresql.conf`: Production PostgreSQL configuration
- `test_database.py`: Comprehensive database tests
- `deploy.sh`: Updated deployment script

## 🐛 Troubleshooting

### Common Issues

**Connection Errors**
```bash
# Check PostgreSQL status
sudo service postgresql status

# Test connection
pg_isready -h localhost -p 5432 -U oluseyioyetunde
```

**Permission Issues**
```bash
# Fix database permissions
sudo -u postgres psql
GRANT ALL PRIVILEGES ON DATABASE swath_movers TO oluseyioyetunde;
```

**Migration Issues**
```bash
# Clear migration lock
rm migration.lock

# Re-run migrations
python app.py
```

## 📞 Support

For issues or questions:
1. Check the logs: `tail -f backup.log`
2. Run tests: `python test_database.py`
3. Verify PostgreSQL: `pg_isready -h localhost -p 5432`

## 🎯 Next Steps

- [ ] Monitor database performance
- [ ] Set up database monitoring (pg_stat_statements)
- [ ] Implement database replication for high availability
- [ ] Set up automated failover
- [ ] Performance tuning based on usage patterns

---

**Migration completed on:** $(date)
**PostgreSQL Version:** 15+
**Python Dependencies:** psycopg2-binary, pandas, flask
