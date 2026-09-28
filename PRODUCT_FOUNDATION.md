# FindMyFrame — product foundation

## Product decision

The first release is an attendee-first experience: bring a local event photo collection, give FindMyFrame one selfie, and receive a quiet, personal gallery. The interface intentionally hides computer-vision vocabulary. The current client is a polished vertical slice with a local-file demo path; production matching remains a replaceable service boundary rather than a fake browser-side claim.

## Recommended architecture

```text
Next.js / React client
  ├─ event intake (local folder or ZIP first; Drive adapter later)
  ├─ selfie capture and privacy consent
  ├─ job progress + result gallery
  └─ signed image URLs / viewer

API service (FastAPI)
  ├─ POST /events
  ├─ POST /events/:id/photos (multipart or presigned upload)
  ├─ POST /search-sessions/:id/reference
  ├─ GET  /search-sessions/:id/status (SSE later)
  └─ GET  /search-sessions/:id/matches

Workers
  ├─ validate + resize + thumbnail
  ├─ detect faces (InsightFace / ArcFace)
  ├─ isolate embeddings from ordinary metadata
  └─ pgvector or FAISS search + confidence bucketing

Storage / data
  ├─ S3-compatible private originals + thumbnails
  ├─ PostgreSQL: Event, Photo, DetectedFace, SearchSession, Match
  └─ short-lived job artifacts with explicit retention policy
```

## Visual direction

- Warm paper background, charcoal ink, rust-orange accent, and image-led color.
- Editorial serif display type paired with a calm grotesk body face.
- Asymmetric compositions and generous negative space instead of dashboard cards.
- Motion is reserved for progress, image reveal, and viewer transitions.
- Privacy is visible at the point of selfie upload and processing, not buried in a footer.

## Core journey

`landing → event collection → selfie → processing → personal gallery → photo viewer`

The working slice includes local multi-file ingestion, sample event fallback, selfie preview, an intentionally labeled demo processing state, responsive gallery, uncertain-match grouping, and individual download affordances. Google Drive is deliberately not presented as working until OAuth, folder permissions, and safe URL ingestion are implemented.

## Technical risks / mitigations

- **Drive ingestion:** use a provider adapter and OAuth-scoped folder access; never fetch arbitrary URLs from the server.
- **Face recognition:** treat matches as ranked suggestions, tune thresholds on representative event data, and provide an uncertain bucket instead of overclaiming.
- **Large collections:** presigned multipart upload, worker queue, thumbnails, bounded batches, and incremental status events; never load the full collection into browser memory.
- **Privacy:** event-scoped IDs, private storage, signed URLs, separated embeddings, retention controls, and clear deletion behavior before making guarantees.
- **Processing time:** index the event once, cache embeddings, and query one reference embedding; stream progress from the worker.
