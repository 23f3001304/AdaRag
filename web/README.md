# AdaRag web

The frontend for AdaRag: an engineered-SaaS dashboard over the FastAPI backend.

- **Stack:** Next.js 16 (App Router) + React 19 + Tailwind v4 + IBM Plex.
- **Design:** dark, Linear/Vercel lineage, a single lime accent. See `app/globals.css` for the tokens.

## Run

The dev server proxies `/api/*` to the backend, so set `BACKEND_URL` to wherever it runs
(host API on `:8001`, or the Docker `api` service on `:8000`, the default):

    npm install
    BACKEND_URL=http://localhost:8001 npm run dev

Then open http://localhost:3000.

## Layout

- `app/` - routes (App Router). `layout.tsx` wires fonts + the shell; `page.tsx` is the overview.
- `components/` - `app-shell.tsx` (sidebar + topbar) and `ui.tsx` (Button, Panel, Badge, Stat).
- `lib/` - `api.ts` (typed backend client) and `cn.ts` (class merge).
