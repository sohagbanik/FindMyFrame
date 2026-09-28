# FindMyFrame

FindMyFrame helps people find the photographs they are in. The repository contains the editorial React/Vite experience, a local FastAPI ingestion foundation, and the first real face-processing pipeline.

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

### Face model setup

The face pipeline uses pretrained OpenCV Zoo ONNX weights: YuNet for detection and SFace-MobileFaceNet for learned face embeddings. No model training or dataset is involved. Install dependencies in the virtual environment, then download and verify the public model files once:

```bash
.venv\Scripts\python backend/download_models.py
```

The downloader verifies the expected SHA-256 checksums. Model files are stored in `backend/models/`, are ignored by Git, and are never downloaded from an API request. CPU inference is the default; set `FINDMYFRAME_CV_DEVICE=cuda` only with a compatible CUDA-enabled OpenCV runtime.

The API exposes:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Development health check |
| POST | `/api/collections` | Create an event-scoped collection |
| POST | `/api/collections/{id}/photos` | Ingest multiple JPG, PNG, or WEBP files |
| POST | `/api/collections/{id}/selfie` | Ingest one temporary reference image |
| POST | `/api/collections/{id}/process-faces` | Queue event-photo face detection and embedding |
| POST | `/api/collections/{id}/process-selfie` | Detect exactly one face and embed the selfie |
| POST | `/api/collections/{id}/match` | Rank real photo matches by embedding similarity |
| GET | `/api/collections/{id}/photos/{photo_id}` | Controlled image retrieval for a collection photo |
| POST | `/api/collections/{id}/import/google-drive` | Import link-accessible Drive folder images |
| GET | `/api/collections/{id}` | Read collection and ingestion status |

Uploaded originals are kept outside Git under `backend/runtime/collections/<collection_id>/`. Metadata is stored in `backend/runtime/collections.json` for development. The storage and repository adapters are deliberately replaceable with S3/Supabase and PostgreSQL later.

## Face Recognition Architecture

```text
Image
  ↓
Image validation + EXIF orientation
  ↓
YuNet face detection
  ↓
SFace-MobileFaceNet aligned face embedding
  ↓
Private JSON development persistence
  ↓
Selfie embedding
  ↓
Cosine similarity
  ↓
Configurable threshold filtering
  ↓
Photo grouping and ranking
  ↓
Real results
```

The model runs during inference only. Face boxes, detector confidence, native embedding vectors, model checksums, and processing state stay backend-side. The same SFace model processes event faces and the selfie. No names, identity profiles, third-party AI APIs, vector search, or final matching are implemented yet.

For event photos, no-face images are valid and continue through the batch. Small faces are recorded without an embedding; image/model errors are attached to that photo rather than aborting the whole collection. Selfies require exactly one usable face and return structured errors for zero or multiple faces.

### Matching thresholds

`FACE_MATCH_STRONG_THRESHOLD` and `FACE_MATCH_POSSIBLE_THRESHOLD` are initial development values, not universally valid biometric boundaries. They must be calibrated empirically against representative event data before production use. The current matcher compares normalized 128-dimensional vectors with cosine similarity, keeps the best face score per photo, and never returns raw embeddings to the frontend.

### Google Drive folder links

The MVP accepts a Google Drive folder URL such as `https://drive.google.com/drive/folders/FOLDER_ID`. The folder must be accessible to anyone with the link, and the backend needs a Google Drive API key with the Drive API enabled. Set `GOOGLE_DRIVE_API_KEY` in the backend environment; never expose it to the frontend or commit it.

The importer uses the official Drive API, paginates image discovery, requests `resourceKey`, `modifiedTime`, and `capabilities.canDownload`, sends documented `X-Goog-Drive-Resource-Keys` headers when keys are available, supports JPEG/PNG/WEBP, downloads bytes through the existing ingestion/validation/storage path, and deduplicates repeated imports with Drive file IDs. A folder can be listable while individual file bytes remain non-downloadable to an API-key-only client; those files are reported individually instead of failing the whole import. OAuth/private-folder access, Drive subfolder traversal, and Google account linking are intentionally not implemented.

## Current limitations

- Authentication and private-folder Google Drive OAuth are not implemented.
- The existing processing/results screens still use the frontend demo path when a sample collection is selected.
- Real local image uploads are sent to the FastAPI ingestion endpoints when the backend is running.
- Invalid or oversized files are rejected with structured JSON errors; mixed uploads return successful photos plus `failed_files`.
- Real uploaded collections are indexed by the backend, but the gallery does not claim matches until Phase 5 adds similarity search and ranking.
