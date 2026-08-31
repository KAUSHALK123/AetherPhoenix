# AetherPhoenix Deployment & Operations Guide

**Version:** 1.0  
**Status:** Implemented (Sprint 10)

---

## 1. Overview

This document defines the deployment, environment configuration, database management, and service health check guidelines for staging and production instances of AetherPhoenix.

---

## 2. Environment Configuration Reference

Configuration is managed dynamically via environment variables (`.env`). No sensitive credentials or hardcoded development values are committed to source control.

### Backend Environment Variables (`backend/.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `development` | Runtime environment (`development`, `staging`, `production`, `testing`) |
| `DEBUG` | `False` | Enable debug mode |
| `HOST` | `0.0.0.0` | Bind host address |
| `PORT` | `8000` | Server listening port |
| `SECRET_KEY` | *(Set in Prod)* | Cryptographic secret key |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | JSON array or list of allowed CORS origin URLs |
| `DATABASE_URL` | `sqlite:///./aether_phoenix.db` | SQLAlchemy connection string |
| `LOG_LEVEL` | `INFO` | Minimum log severity level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_FORMAT_JSON` | `True` | Structured JSON log output |
| `ARTIFACTS_DIR` | `artifacts` | Directory path for generated deliverables |
| `MAX_WORKERS` | `4` | Maximum concurrent execution thread pool size |

### Frontend Environment Variables (`frontend/.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `VITE_API_URL` | `http://localhost:8000` | Base HTTP endpoint of the backend API server |

---

## 3. Local & Manual Production Build

### Backend Startup

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
python -m alembic upgrade head

# Production uvicorn command (without reload)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend Build & Preview

```bash
cd frontend
npm install

# Create production build bundle (dist/)
npm run build

# Preview production build locally
npm run preview
```

---

## 4. Docker Deployment Orchestration

### Staging / Development Compose

```bash
# Build and start services
docker-compose up --build -d

# Check service logs
docker-compose logs -f

# Check health status
docker-compose ps
```

### Production Compose (`docker/docker-compose.prod.yml`)

```bash
# Start production containers
docker-compose -f docker/docker-compose.prod.yml up --build -d

# Stop production containers
docker-compose -f docker/docker-compose.prod.yml down
```

---

## 5. Health Monitoring & Restart Behavior

- **Health Endpoint**: `GET /health` returns JSON:
```json
{
  "status": "ok",
  "project": "AetherPhoenix",
  "version": "0.1.0",
  "environment": "production",
  "database": "connected"
}
```
- **Container Health Check**: Evaluated every 10–15 seconds via `http://localhost:8000/health`.
- **Restart Policy**: Containers are configured with `restart: unless-stopped` (development) or `restart: always` (production).
