# API Reference

Base URL: `http://127.0.0.1:8000`

Auth: protected endpoints require `Authorization: Bearer <token>`.

## Auth

- POST `/api/auth/login`
- GET `/api/auth/me`
- POST `/api/auth/change-password`
- GET `/api/auth/password-policy`
- POST `/api/auth/users`
- POST `/api/auth/users/{username}/reset-password`
- GET `/api/auth/users`

## Sessions

- GET `/api/auth/sessions`
- DELETE `/api/auth/sessions/{session_id}`
- POST `/api/auth/sessions/revoke-all`
- POST `/api/auth/users/{username}/sessions/revoke-all`
- POST `/api/auth/logout`

## Records

- GET `/api/records`
- GET `/api/records/{record_id}`
- POST `/api/records`
- PUT `/api/records/{record_id}`
- DELETE `/api/records/{record_id}`
- POST `/api/records/batch-delete`
- POST `/api/records/batch-update`

## Import / Export

- GET `/api/export/csv`
- GET `/api/export/excel`
- GET `/api/export/pdf` (supports `limit` query param)
- POST `/api/import`
- POST `/api/import/preview`
- GET `/api/template/csv`
- GET `/api/template/excel`

## Public Query

- GET `/api/query` (composition query)
- POST `/api/query/by-components`
- POST `/api/query/range`
- POST `/api/query/match-count`
- POST `/api/query/hydrate`
- POST `/api/query/batch/hydrate`
- POST `/api/query/batch/by-components`

## Query History and Favorites (auth)

- GET `/api/query/history`
- GET `/api/query/favorites`
- POST `/api/query/favorites`
- DELETE `/api/query/favorites/{favorite_id}`

## Charts

- GET `/api/charts/temperature`
- GET `/api/charts/pressure`
- GET `/api/charts/scatter`
- GET `/api/charts/composition`
- POST `/api/charts/cache/clear`

## Review

- GET `/api/review/duplicates`
- POST `/api/review/move-duplicates`
- GET `/api/review/pending`
- GET `/api/review/stats`
- PUT `/api/review/pressure/{pending_id}`
- POST `/api/review/approve/{group_id}`
- POST `/api/review/approve-batch`
- POST `/api/review/reject/{group_id}`
- POST `/api/review/reject-batch`
- POST `/api/review/restore/{group_id}`
- POST `/api/review/restore-batch`

## Backup (admin)

- GET `/api/backup/status`
- GET `/api/backup/list`
- POST `/api/backup/create`
- POST `/api/backup/restore/{filename}`
- DELETE `/api/backup/{filename}`
- GET `/api/backup/download/{filename}`

Note: `/api/backup/download/{filename}` supports `?token=<access_token>` for
browser downloads when custom headers are not available.
