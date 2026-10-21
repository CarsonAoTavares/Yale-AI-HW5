# Campus Customs: Multi-Agent Operations (Homework 5)

A team of five AI agents (Boss, Inventory, Accounting, Facilities, Customer Service) works the Campus Customs operations board. They read and update the shop's database only through an MCP server, a FastAPI backend runs the team, and a React dashboard lets a person watch the agents and approve every payment.

- **MCP server:** `mcp_server/server.py` (FastMCP) over `data/campus_customs_new.db`
- **Backend:** `backend/` (FastAPI + PydanticAI). Every agent uses Claude Opus 5.5 (`claude-opus-5-5`, low effort) through the Anthropic API. The graded submission on `main` used `gpt-6-luna` through Portkey.
- **Dashboard:** `frontend/` (React + Vite + TypeScript)
- **Docs and evidence:** `output/` (`harness.md` has the full system description)

## Setup

You need Python 3.12+ and Node 20+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then put your ANTHROPIC_API_KEY in .env
cd frontend && npm install && cd ..
```

## 1. Make a clean working database

`data/campus_customs.db` is the original and is never modified. The agents and tools only touch the working copy, `data/campus_customs_new.db`. When you need a clean run, copy the original over the working copy:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

## 2. Start the MCP server

The backend starts the MCP server on its own (over stdio) whenever the agents or routes need it, so you don't have to start it separately to use the app. To run it by hand, for example to test the tools:

```bash
CAMPUS_CUSTOMS_DB=data/campus_customs_new.db .venv/bin/python mcp_server/server.py
```

`.mcp.json` registers the same server for a coding assistant such as Claude Code, so it can call the tools directly.

## 3. Start the FastAPI backend

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

The API is at http://localhost:8000 (interactive docs at http://localhost:8000/docs). The routes are listed in `output/harness.md`.

## 4. Start the React board

In a second terminal:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173. Pick a ticket, click **Dispatch the team**, watch the agents work, and approve or reject the payments they prepare.

## 5. Reset before a full three-ticket run

Before running tickets 101, 102, and 103 end to end, restore the working database so every run starts from the same data. Either click **↺ Fresh run** in the dashboard header, or:

```bash
curl -X POST http://localhost:8000/api/reset
```

This copies `campus_customs.db` over `campus_customs_new.db` and voids any pending approvals left from the previous run. The audit trail in `output/audit_trail.json` is append-only and is not cleared.

## Deploy online (Render, free)

The `Dockerfile` builds the React board and serves it from the FastAPI backend, so the whole app is one web service.

1. On https://render.com choose **New → Blueprint** and pick this repo and the `deploy` branch (it reads `render.yaml`).
2. When asked, paste your `ANTHROPIC_API_KEY`. Never commit it.
3. Render builds the image and gives you a `*.onrender.com` link. It redeploys on every push to `deploy`.

The free plan sleeps after 15 minutes idle, so the first load can take about a minute. Its disk is not kept between deploys: the database goes back to the committed copy each time.

## Safety in one paragraph

Agents never send messages or move money. Customer, vendor, and landlord messages are drafts on the board. Payments and purchase orders are prepared as approval requests. Only a person clicking **Approve** calls the payment tool, which agents can't see, and that tool refuses any payment that would make a balance negative. Each ticket run is capped at 60 model requests and 400,000 tokens. Details are in `output/harness.md`.
