# React + Vite

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
