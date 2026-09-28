# FindMyFrame

FindMyFrame helps people find the photographs they are in. The current repository contains the editorial React/Vite experience from Phases 1–2 and a local FastAPI ingestion foundation from Phase 3.

## Run the frontend

```bash
npm install
npm run dev
```

The frontend defaults to `http://localhost:5173` and reads the backend URL from `VITE_API_URL` (default: `http://localhost:8000`). Copy `.env.example` to `.env` only when you need to override local defaults; never commit `.env`.

## Run the backend

Python 3.11+ is recommended.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

The API exposes:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Development health check |
| POST | `/api/collections` | Create an event-scoped collection |
| POST | `/api/collections/{id}/photos` | Ingest multiple JPG, PNG, or WEBP files |
| POST | `/api/collections/{id}/selfie` | Ingest one temporary reference image |
| GET | `/api/collections/{id}` | Read collection and ingestion status |

Uploaded originals are kept outside Git under `backend/runtime/collections/<collection_id>/`. Metadata is stored in `backend/runtime/collections.json` for development. The storage and repository adapters are deliberately replaceable with S3/Supabase and PostgreSQL later.

## Phase 3 limitations

- Face detection, embeddings, similarity search, authentication, and Google Drive are not implemented.
- The existing processing/results screens still use the frontend demo path when a sample collection is selected.
- Real local image uploads are sent to the FastAPI ingestion endpoints when the backend is running.
- Invalid or oversized files are rejected with structured JSON errors; mixed uploads return successful photos plus `failed_files`.

## CV extension point

`backend/app/services/face_service.py` and `matching_service.py` define explicit boundaries for the future worker pipeline:

```text
ingested photo → face detection → embedding storage
reference selfie → embedding → similarity search → ranked matches
```

Phase 3 intentionally does not create fake embeddings or claim that ingestion is matching.
