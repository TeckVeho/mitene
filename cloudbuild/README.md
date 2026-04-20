# Cloud Build configs

YAML files in this directory build Docker images and (for `cloudbuild.*.yaml` without `-api`/`-web` suffix) deploy to Cloud Run. Image URLs use **`_AR_PROJECT_ID`** (Artifact Registry / common project) and deploy steps use **`_DEPLOY_PROJECT_ID`** (app project). If those substitutions are empty, steps fall back to **`$PROJECT_ID`** (the project where the build runs).

## Branch triggers (example)

Create one trigger per branch (or use regex) in the GCP project where builds execute. Set **Substitution variables** so each environment gets the right registry and deploy target.

| Branch (example) | Config file | Typical substitutions |
|------------------|-------------|------------------------|
| `develop` | `cloudbuild.dev.yaml` | `_AR_PROJECT_ID=<common-project>`, `_DEPLOY_PROJECT_ID=<dev-project>`, `_TAG=dev`, `_NEXT_PUBLIC_*` → dev URLs |
| `staging` | Reuse `cloudbuild.dev*.yaml` with `_TAG=stage` (or dedicated stg YAML) | `_DEPLOY_PROJECT_ID` → staging app project |
| `main` | `cloudbuild.prod.yaml` | `_AR_PROJECT_ID=<common-project>`, `_DEPLOY_PROJECT_ID=<prod-project>`, `_TAG=prod`, `_NEXT_PUBLIC_*` → prod URLs |

**IAM — Cloud Build execution SA**

GCP uses either the legacy Cloud Build SA (`PROJECT_NUMBER@cloudbuild.gserviceaccount.com`) or the Compute Engine default SA (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`) to **execute** builds. This SA needs:

- **`roles/storage.objectAdmin`** on the build project — read source from `gs://PROJECT_ID_cloudbuild`.
- **`roles/artifactregistry.writer`** on the **common** Artifact Registry project (see [`infra/terraform/common`](../infra/terraform/common) variable `additional_artifact_registry_writer_members`).
- **`roles/logging.logWriter`** on the build project — full step logs in Cloud Logging (optional but recommended).
- **`roles/run.admin`** + **`roles/iam.serviceAccountUser`** on **`_DEPLOY_PROJECT_ID`** (the app project, e.g. `veho-mitene`) so `gcloud run deploy` succeeds — **not** only on the project where `gcloud builds submit` runs.

Check which SA your project uses: **Cloud Build → Settings** in Console. See [`GITHUB_ACTIONS_WIF.md`](GITHUB_ACTIONS_WIF.md) Step 6 for full commands.

**Split configs** (`*-api.yaml`, `*-web.yaml`): build, push, then deploy the matching Cloud Run service (API or web only). Set `_AR_PROJECT_ID` when the registry lives in the common project.

**GitHub Actions** — [`.github/workflows/cd-gcp.yml`](../.github/workflows/cd-gcp.yml) passes `--substitutions` including `_AR_PROJECT_ID` / `_DEPLOY_PROJECT_ID` from Environment variables **`GCP_AR_PROJECT_ID`** / **`GCP_DEPLOY_PROJECT_ID`**. The workflow resolves empty values to `$PROJECT_ID` in bash **before** calling `gcloud builds submit`, so Cloud Build YAML only contains `${_*}` substitutions. See [`GITHUB_ACTIONS_WIF.md`](GITHUB_ACTIONS_WIF.md).

See also [`scripts/gcp/README.md`](../scripts/gcp/README.md).

## Cloud Build substitution syntax

All YAML files use only Cloud Build user-defined substitutions (`${_TAG}`, `${_AR_PROJECT_ID}`, etc.) — **no bash local variables** inside step scripts. This avoids `INVALID_ARGUMENT: key in the template "…" is not a valid built-in substitution` errors, since Cloud Build scans all `$IDENT` / `${IDENT}` patterns in the YAML and rejects anything that is not a built-in or `_`-prefixed user substitution.
