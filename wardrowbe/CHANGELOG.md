# Changelog

## 4.3.4

- Update upstream Wardrowbe from v1.10.1 to v1.10.2, including
  wardrobe composition analytics fixes,
  refreshed item edit forms, editable subtypes, and translation corrections.
- Replace the legacy `addon_config` map type with `app_config` to remove
  the Supervisor validation warning.

## 4.3.3

- Update upstream Wardrowbe from v1.10.0 to v1.10.1 to handle AI provider
  errors returned with HTTP 200 and retry unsupported parameters correctly.

## 4.3.2

- Fix PostgreSQL connection exhaustion after login by increasing the managed
  connection limit from 10 to 50 for the backend and both worker pools.
  Existing installations receive the updated setting on app restart.
- Add a container regression check for concurrent database connections.

## 4.3.1

- Update upstream Wardrowbe from v1.8.0 to v1.10.0, including base-item
  outfit suggestions, three-look comparison, weather-aware scoring, and
  AI timeout and upload-queue fixes.
- Start a dedicated image worker for the upstream image-processing queue
  so queued photo rotations and background-removal jobs are consumed.
- Wait for backend health before starting the image worker, and let s6
  retry startup if the backend is unavailable.
