# React + Vite

## classi-service

The `/#/classi` route has two deliberately separate modes:

- **Production build:** a restricted classification-only Azure preview. The
  owner enters the preview key into the page at runtime; it is sent to Azure
  over HTTPS and kept in component memory until leaving or refreshing. It is
  not bundled or persisted. Anyone with the key can use the API, so use a
  trusted device and never share it on screen. The exact deployed origin must
  be allowed by the Azure API's CORS settings; CORS is not authentication.
  Graph, admin and performance pages are not available in the cloud preview.
- **Local development:** the existing playground, performance monitor, graph
  workspace and admin review page use the separate local classi-service API
  and worker, not `gpai-backend`. Start those services using the classi-service
  project README; the API defaults to `http://127.0.0.1:8000`, configurable
  with `VITE_CLASSI_API`. `VITE_CLASSI_PREVIEW=cloud` selects the cloud UI for
  development, but its API still requires a CORS-allowed origin.

Use fictional data only. Local graph submissions are opt-in and retain the
transcript for admin review; classification alone does not retain it. The
Azure F1 instance may be slow to start and uses a shared preview key without
per-user revocation or rate limiting.

### Current capabilities and phase 2.1

- The Azure preview accepts JSON classification requests with runtime-supplied
  classes and returns the best label or `ndw` with scores and timing. It
  requires the shared preview key and supports the portfolio origin.
- The hosted portfolio provides an owner-operated classifier with example
  scenarios and runtime key entry; it does not persist the key.
- The local application offers the separate graph queue, worker, canvas,
  minimap and admin review. These are not available in the Azure preview.
- **Phase 2.1:** connect durable cloud graph storage and a separate worker,
  preserving consent, review, retry and deletion semantics; secure access
  separately for demo users and administrators. No cloud graph functionality
  is claimed until it is implemented and verified.

## kg-bi concept demo

The portfolio's `/#/kg-bi` page illustrates an automotive support knowledge
graph using fictional conversations and predefined entities and relationships.
Select graph nodes or links to inspect examples, filter entity types, switch
conversation excerpts, and confirm or reject proposed links. Changes are
temporary and reset when the page is reloaded or the sample is reset.

This is a frontend-only concept: it does not ingest conversations, perform
live NER or PII detection, persist a graph, or provide an agent-memory API.
The illustrated workflow and agent memory are future possibilities, not
implemented services. Do not enter real customer data into the demo.

## int-pii portfolio demo

The PII console at `/#/pii` uses a separate Render service, not the existing
`gpai-backend`. Provision `int-pii-backend` using the entry in `render.yaml`,
set its `ALLOWED_ORIGINS` to the exact Vercel origin(s), and configure the
frontend's `VITE_PII_API_URL` in Vercel to the new service's HTTPS URL. Redeploy
the frontend after setting this build-time variable. Until both services and
the variable are configured, the hosted PII demo will not work. The free plan
has limited memory; if model loading fails or the service restarts, check the
Render logs and upgrade the isolated service if necessary.

The PII service permits the production Vercel origin by default. If
`ALLOWED_ORIGINS` is set in Render, it replaces that default: include the exact
frontend origin in its comma-separated list. A failed Render proxy response
may also appear in the browser as a CORS error because it can be returned
before the application adds CORS headers. Check the service logs and retry
after a cold start or restart rather than assuming every such error is an
origin configuration issue.

For local development, start `uvicorn app.pii_main:app --host 127.0.0.1 --port
8001` from `backend` using the dependencies in `pii-requirements.txt`, and run
the frontend normally. The frontend defaults to `http://localhost:8001` only
in development. Configure `ALLOWED_ORIGINS` when using a different frontend
origin.

This is a public demonstration, not a secure PII processing service. Use
synthetic data only. Files are sent to the server and retained in memory for
approximately 30 minutes or until discarded; a restart also clears sessions.
Uploaded filenames may appear in service access logs.
Evaluation uses synthetic data only. It runs in a background job, one at a
time, and results are temporary. Saved run summaries are held in memory.

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is enabled on this template. See [this documentation](https://react.dev/learn/react-compiler) for more information.

Note: This will impact Vite dev & build performances.
You can also try [the experimental native React Compiler support in plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md#rust-react-compiler) by using `compiler: true` in the plugin options instead of using the Babel plugin.

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.
