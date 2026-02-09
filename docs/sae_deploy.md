# SAE Deployment Checklist

## Build & Push Image

```bash
docker build -t <acr-registry>/<namespace>/gas-app:<tag> .
docker push <acr-registry>/<namespace>/gas-app:<tag>
```

## SAE App Configuration

- **Image**: use the pushed ACR image.
- **Port**: `8000` (matches `uvicorn` in `Dockerfile`).
- **Health Check**: `GET /api/statistics`
- **CPU/Memory**: 0.5-1 vCPU / 1-2 GB for small traffic.
- **Deployment**: rolling release or gray release.

## Environment Variables

- `DATABASE_URL` (MySQL RDS connection string)
- `SECURITY_DATABASE_URL` (optional, defaults to `DATABASE_URL`)
- `SECRET_KEY`
- `ADMIN_PASSWORD`
- `CORS_ORIGINS` (comma-separated)
- `REDIS_URL` (optional, for rate-limit/session sharing)
- `DB_POOL_ENABLED` (`1` default)
- `DB_POOL_MAX` / `DB_POOL_MIN` / `DB_POOL_MAX_CACHED`
- `DB_CONNECT_TIMEOUT` / `DB_READ_TIMEOUT` / `DB_WRITE_TIMEOUT`

## Networking

- Deploy SAE into the same **VPC** as RDS.
- Use **intranet endpoint** for `DATABASE_URL`.
- Ensure security group allows SAE to access RDS on port `3306`.

## Release Steps

1. Apply migrations: `python3 scripts/migrate_db.py --target all`
2. Run smoke tests on staging environment.
3. Gray release to production.
4. Monitor errors/latency; rollback if needed.

## Backup

- Use RDS automated backups (daily + retention).
- Monthly restore drill on a temporary instance.
