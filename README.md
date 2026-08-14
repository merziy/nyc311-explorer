# NYC 311 Explorer

A "chat with your data" app over NYC's 311 service request dataset — filter, browse, and map hundreds of thousands of real 311 complaints, or just ask a question in plain English.

**Live:** [nyc311-explorer.alexzandermathis.workers.dev](https://nyc311-explorer.alexzandermathis.workers.dev)

## Features

- **Interactive map** — heatmap and cluster views of complaint density across NYC, built on MapLibre GL with free OpenFreeMap vector tiles
- **Ask a question** — natural-language queries ("what are the top complaints in Bushwick this summer?") answered by Claude, which turns the question into a structured filter, runs it against Postgres, and summarizes the results in plain English
- **Filters** — borough, complaint type, and date range, shared across the map, table, and top-complaints breakdown
- **Click-to-inspect** — click any point on the map for that complaint's full details, including the responding agency's resolution notes
- **Light/dark theme**, following the system by default with a manual override

## Tech stack

| | |
|---|---|
| Backend | Flask, Flask-SQLAlchemy, Postgres, Claude (tool use) |
| Frontend | Vue 3, Vite, MapLibre GL JS |
| Data | NYC Open Data (Socrata), ~ monthly rolling window, refreshed daily |
| Hosting | Render (API), Neon (Postgres), Cloudflare Workers (frontend) |

## Running it locally

```bash
# Postgres
docker compose up -d

# Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp ../.env.example .env   # fill in ANTHROPIC_API_KEY and SOCRATA_APP_TOKEN
.venv/bin/flask db upgrade
.venv/bin/python -m scripts.ingest_311   # pulls real 311 data — takes a few minutes
FLASK_APP=app.main .venv/bin/flask run --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Opens on `http://localhost:5173`. See [`CLAUDE.md`](./CLAUDE.md) for full architecture notes, environment variables, and deployment details.
