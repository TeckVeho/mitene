# Mitene — Google Cloud Build

Build and push container images to **Artifact Registry** (`mitene-docker` repository; create via Terraform or `gcloud`).

Prerequisites:

- `gcloud` CLI authenticated (`gcloud auth login`)
- Project set: `gcloud config set project YOUR_PROJECT_ID`
- Artifact Registry repository exists (e.g. `mitene-docker`, Docker format, same region as `_REGION`)

## API (FastAPI)

From the **repository root** (parent of `backend/`):

```bash
# Dev tag
gcloud builds submit --config=cloudbuild/cloudbuild.dev.api.yaml .

# Production tag
gcloud builds submit --config=cloudbuild/cloudbuild.prod.api.yaml .
```

## Web (Next.js standalone)

Set `NEXT_PUBLIC_API_URL` to the **public URL of the Mitene API**, including the `/api` path prefix (see `frontend/.env.example`).

```bash
gcloud builds submit --config=cloudbuild/cloudbuild.dev.web.yaml \
  --substitutions=_NEXT_PUBLIC_API_URL=https://mitene-api-dev-xxxxx.asia-northeast1.run.app/api
```

```bash
gcloud builds submit --config=cloudbuild/cloudbuild.prod.web.yaml \
  --substitutions=_NEXT_PUBLIC_API_URL=https://api.your-domain.com/api
```

## Substitutions

| Variable | Default (in YAML) | Purpose |
|----------|-------------------|---------|
| `_REGION` | `asia-northeast1` | Region for Artifact Registry image URL |
| `_REPO` | `mitene-docker` | Artifact Registry repository id |
| `_TAG` | `dev` / `prod` | Image tag |
| `_NEXT_PUBLIC_API_URL` | placeholder | **Web only** — baked into the client bundle at build time |

`NEXT_PUBLIC_*` variables are **compile-time** for the Next.js client; set them via Cloud Build `--substitutions` (or Dockerfile `ARG`/`ENV`) when building the web image — not only at Cloud Run runtime.

After images exist, point Terraform `container_image` / `web_container_image` at:

`REGION-docker.pkg.dev/PROJECT_ID/mitene-docker/mitene-api:TAG`
