# One web service: FastAPI serves the API, the MCP server (spawned over stdio),
# and the built React board.

FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY backend/ backend/
COPY mcp_server/ mcp_server/
COPY data/campus_customs.db data/campus_customs_new.db data/
COPY output/ output/
COPY --from=frontend /frontend/dist frontend/dist
WORKDIR /app/backend
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
