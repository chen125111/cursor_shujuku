# Ops & Monitoring Checklist (Aliyun)

## Observability

- Enable SLS for application logs (stdout/stderr).
- Enable ARMS/Tracing for API latency, error rate, and slow requests.
- Configure CloudMonitor metrics for ECS/SAE and RDS.

## Alerts (Suggested)

- API error rate > 2% for 5 minutes.
- P95 latency > 1s for 5 minutes.
- RDS connections > 80% of limit.
- RDS CPU > 70% for 10 minutes.
- Disk usage > 80% on RDS.
- Backup failure or missing daily backup.

## Release Safety

- Use SAE gray/rolling release and keep one previous version for fast rollback.
- Apply DB migrations in low-traffic windows and monitor error rate post-release.

## Backup & Recovery

- Enable daily automated backup on RDS (7-30 days retention).
- Perform monthly restore drills to a temporary instance.
