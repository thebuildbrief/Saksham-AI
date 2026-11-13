# Saksham AI — Vercel deployment and environment guide

This repository is configured as **two separate Vercel projects** linked to the same GitHub repository:

- **Frontend project root:** frontend
- **Backend project root:** backend

The original frontend and most backend application modules were absent from the available Git commit/history and local backups. The current frontend and recovered backend modules are implemented in the existing repository; they are not restored historical source. This guide describes the current implementation.

## 1. Deployment order

1. Provision PostgreSQL, Redis, private S3-compatible object storage, an AI provider, and Judge0.
2. Apply the SQL migrations in order (section 3).
3. Create the Vercel backend project with root directory backend, connected to this repository and the intended branch.
4. Set every required Production environment variable below. Set Preview values separately if Preview deployments are used.
5. Deploy the backend and verify https://<backend-domain>/health, /docs, and authentication.
6. Create the Vercel frontend project with root directory frontend.
7. Set VITE_API_URL=https://<backend-domain> in the frontend project for the same deployment environment, then deploy.
8. Set backend FRONTEND_ORIGINS to the exact deployed frontend origin (no path or trailing slash), redeploy backend, and test from the browser.
9. Run the staging and end-to-end checks in section 6 before directing real users to the deployment.

Do not deploy until PostgreSQL migrations and all required provider credentials are configured. APP_ENV=production deliberately rejects missing integrations.

## 2. Vercel project settings

### Backend (backend root)

- Framework preset: Other (Vercel should detect Python from api/index.py).
- Install command: pip install -r requirements.txt (or leave Vercel's Python dependency install detection enabled).
- Build command: leave blank unless Vercel requires one.
- Output directory: leave blank.
- Entry point: api/index.py, exporting the FastAPI app.
- vercel.json rewrites requests to the function.
- Set a function duration appropriate for your Vercel plan and expected Judge0 latency. The app enforces a 30-second overall provider deadline; do not configure the function below this budget.
- Vercel's serverless request/response body cap is 4.5 MB. The API caps resumes at 3 MiB plus multipart overhead, remaining below that limit. Check current plan limits before raising the cap.

### Frontend (frontend root)

- Framework preset: Vite.
- Install command: npm ci.
- Build command: npm run build.
- Output directory: dist.
- Node.js: 22.12 or newer.
- vercel.json routes SPA paths to index.html.

Vercel references: https://vercel.com/docs/frameworks/backend/fastapi, https://vercel.com/docs/functions/limitations, https://vercel.com/changelog/websocket-support-is-now-generally-available.

## 3. PostgreSQL migrations

The SQL files are additive and intended to preserve existing rows. Run them against the same production database used by the backend, in this order, from the repository root:

~~~sh
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/migrations/20261111_create_core_schema.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/migrations/20261112_add_coding_submission_user_id.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/migrations/20261113_add_platform_tables.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/migrations/20261114_seed_coding_catalog.sql
~~~

On Windows PowerShell:

~~~powershell
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f backend/migrations/20261111_create_core_schema.sql
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f backend/migrations/20261112_add_coding_submission_user_id.sql
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f backend/migrations/20261113_add_platform_tables.sql
psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f backend/migrations/20261114_seed_coding_catalog.sql
~~~

Before using an existing database, take a provider snapshot/backup and verify the current table definitions. These scripts do not remove or rewrite existing rows; however, CREATE TABLE IF NOT EXISTS does not reconcile a pre-existing table with a different column definition. Confirm schema compatibility before applying to any database containing pre-existing Saksham tables. Verify with:

~~~sql
\dt
\d users
\d interview_sessions
\d coding_submissions
\d user_profiles
\d interview_turns
\d resume_documents
\d user_subscriptions
~~~

Mark/check migration completion in your own operational ledger; this repository does not add a schema-version tracker. Never use SQLite for the production backend.

## 4. Backend environment variables

Set these in the backend Vercel project, not the frontend. Values below describe required names; credentials must come from your own providers.

| Variable | Required | Purpose / expected value |
|---|---:|---|
| APP_ENV | Yes | production |
| DEBUG | Yes | false |
| APP_SECRET_KEY | Yes | Random secret, at least 32 characters |
| JWT_SECRET_KEY | Yes | Separate random secret, at least 32 characters |
| FRONTEND_ORIGINS | Yes | Exact HTTPS frontend origin(s), comma-separated; e.g. https://<frontend>.vercel.app |
| DATABASE_URL | Yes | Managed PostgreSQL URL reachable from Vercel; use provider's pooled/serverless URL and TLS settings |
| REDIS_URL | Yes | Managed Redis rediss://... preferred; used for per-user execution rate limits and cross-instance concurrency |
| AI_PROVIDER | Yes | One of openai, gemini, groq, anthropic |
| Provider API key | Yes | Exactly one of OPENAI_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, ANTHROPIC_API_KEY, matching AI_PROVIDER |
| JUDGE0_API_URL | Yes | HTTPS base URL for configured Judge0 service |
| JUDGE0_API_KEY | Yes | Judge0 credential; stays on backend |
| STORAGE_PROVIDER | Yes | s3 |
| STORAGE_S3_BUCKET | Yes | Private bucket name |
| STORAGE_S3_REGION | Yes | Bucket region |
| STORAGE_S3_ACCESS_KEY_ID | Yes | Least-privilege object-storage access key |
| STORAGE_S3_SECRET_ACCESS_KEY | Yes | Secret for the above key |
| STORAGE_S3_ENDPOINT_URL | No | Required only for S3-compatible providers that need a custom endpoint |

Other optional backend variables (configure only if the feature is enabled):

- Database: DATABASE_POOL_SIZE (keep small for serverless; default 1).
- AI: AI_MODEL, AI_REQUEST_TIMEOUT_SECONDS.
- Code execution: CODE_CPU_TIME_LIMIT, CODE_WALL_TIME_LIMIT, CODE_MEMORY_LIMIT_KB, CODE_PROVIDER_TIMEOUT_SECONDS, CODE_REQUEST_TIMEOUT_SECONDS, CODE_MAX_CONCURRENT, CODE_MAX_REQUESTS_PER_MINUTE, CODE_MAX_TEST_CASES.
- Resume limit: MAX_RESUME_SIZE_BYTES (default 3 MiB; Vercel body ceiling still applies).
- Voice: VOICE_PROVIDER=browser by default. For server-side ElevenLabs set VOICE_PROVIDER=elevenlabs, ELEVENLABS_API_KEY, and ELEVENLABS_VOICE_ID.
- Billing: SUBSCRIPTION_PROVIDER=none by default. For Stripe, set SUBSCRIPTION_PROVIDER=stripe, STRIPE_SECRET_KEY, STRIPE_PRICE_ID, STRIPE_WEBHOOK_SECRET; configure Stripe to call /api/v1/subscriptions/webhook.

The backend environment template is backend/.env.example; it contains placeholders only.

## 5. Frontend environment

Set only this public value in the frontend Vercel project:

- VITE_API_URL=https://<backend-project-domain>

Vite embeds VITE_* values in browser JavaScript. Never put database credentials, JWT/app secrets, AI keys, Judge0 keys, Redis URLs, storage credentials, Stripe secret keys, or webhook secrets in the frontend project. After changing VITE_API_URL, rebuild and redeploy the frontend.

The template is frontend/.env.example.

## 6. Staging and end-to-end verification

Use Vercel Preview deployments and non-production provider resources first. Set the backend Preview FRONTEND_ORIGINS to the precise preview frontend origin and set the frontend Preview VITE_API_URL to the preview backend. Wildcard CORS is not supported.

Check in this order:

1. GET /health returns HTTP 200 and {"status":"online",...}.
2. GET /docs loads and contains the expected /api/v1/* routes.
3. Register, log in, refresh token, and call /api/v1/users/me; unauthenticated calls to protected APIs return 401.
4. Start and answer an interview; confirm turns persist, ownership is enforced, and WebSocket clients reconnect using a fresh session-scoped token.
5. Upload, analyze, download, and delete a test resume; verify the object is private and owner-only.
6. Use the coding API with a real configured Judge0 instance: confirm the Judge0 dashboard/provider reports each run isolated, exercise Python and JavaScript, independent public/hidden test inputs, timeout/output errors, quota rejection, and that hidden inputs/expected outputs never appear in responses.
7. Verify AI behavior with your configured provider and ensure provider failures return safe service errors.
8. From the deployed frontend origin, verify browser preflight/CORS and complete sign-in, interview, coding, resume, and settings flows.
9. Confirm logs contain no authorization headers, prompts with sensitive content, provider credentials, or resume contents.

## 7. Known limits and required owner actions

- No live PostgreSQL, Redis, S3-compatible store, AI provider, Judge0, Stripe, or ElevenLabs credentials are included. Supply them through your own Vercel project settings.
- Judge0 network API integration is implemented; isolation strength cannot be claimed until tested with your actual configured Judge0 instance and its runtime/security policy.
- Local tests mock AI/Judge0 and use SQLite. They do not prove external service availability, actual sandbox isolation, production database migration compatibility, Vercel function behavior, or browser deployment connectivity.
- WebSocket support, serverless duration, function body limits, and database connection limits depend on Vercel plan/runtime and provider settings. Confirm them in the project before production use.
- The Vercel CLI session is not authenticated in this workspace, so project creation, preview deployment, and remote environment verification require the project owner to connect their Vercel account.
