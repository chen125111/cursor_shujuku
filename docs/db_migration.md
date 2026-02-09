# Database Migration Guide

This project uses two databases:

- Gas data: `DATABASE_URL`
- Security data: `SECURITY_DATABASE_URL` (falls back to `DATABASE_URL` if unset)

## Apply schema migrations (MySQL/RDS)

```bash
python3 scripts/migrate_db.py --target all
```

## Migrate existing SQLite data to MySQL

```bash
python3 scripts/migrate_sqlite_to_mysql.py \
  --database-url "mysql://user:pass@host:3306/gas_data" \
  --security-database-url "mysql://user:pass@host:3306/security_data"
```

Optional:

- `--force` to truncate target tables before insert.
- `--batch-size` to control import batch size.
