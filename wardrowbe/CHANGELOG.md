# Changelog

## Unreleased

- Update upstream Wardrowbe from v1.8.0 to v1.10.0, including base-item
  outfit suggestions, three-look comparison, weather-aware scoring, and
  AI timeout and upload-queue fixes.
- Start a dedicated image worker for the upstream image-processing queue
  so queued photo rotations and background-removal jobs are consumed.
- Wait for backend health before starting the image worker, and let s6
  retry startup if the backend is unavailable.
