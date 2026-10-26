# Deployment

Production: https://nexus-world-sim.vercel.app (VERIFIED 2026-10-26). One Vercel project, Git-connected to this repository, using Vercel Services (Beta).

| Service | Root | Runtime | Public route |
|---|---|---|---|
| `web` | `frontend/` | Next.js | `/(.*)` |
| `api` | `./` | Python, `nexus.api.vercel_app:app` (FastAPI mounted at `/api`) | `/api/(.*)` |

Configured in `vercel.json`. Runtime Python dependencies come from `requirements.txt` (no TensorFlow; training-only packages live in `requirements-train.txt`).

## Environment variables

| Name | Service | Required | Notes |
|---|---|---|---|
| `OPENAI_API_KEY` | api | For AI mode | Sensitive. Without it the API runs engine-only. |
| `NEXUS_OPENAI_MODEL` | api | No | Defaults to `gpt-6-luna`. |
| `NEXUS_DISABLE_LLM` | api | No | `1` forces engine-only. |
| `NEXT_PUBLIC_SITE_URL` | web | Yes | Canonical URL for metadata and OG images. |
| `NEXUS_BACKEND_URL` | local only | Local | Next rewrite target for `/api`; set at build and start. Not used on Vercel. |

## Deploy flow

Push to `main`; Vercel builds both services and promotes the deployment to production.

## Limits

- Run records are kept in memory per function instance, so `/run/{id}` links work only while that instance is warm.
- Rate limits: POST 30/min, GET 120/min per IP (in memory, per instance).

## Production notes (MEASURED 2026-10-26)

- Project framework preset: `services`. Python 3.13 via `.python-version`. Functions run in iad1.
- Python bundle reported by the build: 289 MB (Vercel optimizes dependencies above the standard size).
- `/_next/image` returned 404 under Services, so `images.unoptimized` is set; logos are pre-resized copies of `logo.png`.
- Security headers on `/api/*` via `vercel.json`; Next.js pages set them in `next.config.ts`.
- `nexus-world.vercel.app` belongs to another account, so the clean alias is `nexus-world-sim.vercel.app`.
