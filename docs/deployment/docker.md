# Docker Deployment

FastPKI ships with Docker Compose configurations for both development and production.

## Dockerfile

The image is based on `python:3.11-slim` and uses `uv` for dependency installation. It runs the application as a non-root `app` user.

The Dockerfile accepts a `VERSION` build argument that sets the `org.opencontainers.image.version` OCI label for image introspection.

```
docker/Dockerfile
```

## Development Mode

Development mode mounts the source tree and enables live reload.

```bash
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
```

What this does:

- Mounts the project root into `/app` so code changes are reflected immediately
- Uses SQLite (stored in `./data/`)
- Starts uvicorn with `--reload`
- PostgreSQL service is available but not started by default (use `--profile postgres` to enable)

## Production Mode

Production mode uses PostgreSQL and does not mount the source tree.

```bash
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
```

What this does:

- Only mounts `./data/` for persistent storage
- Connects to the PostgreSQL service
- Starts uvicorn without `--reload`
- PostgreSQL starts automatically

## Compose Files

### `docker-compose.yml` (base)

Defines the `api` and `db` services. The `db` service (PostgreSQL 15) is placed under the `postgres` profile by default so it only starts when explicitly requested.

### `docker-compose.dev.yml` (development overlay)

- Mounts source code for live reload
- Overrides the command to include `--reload`
- Keeps PostgreSQL behind the `postgres` profile

### `docker-compose.prod.yml` (production overlay)

- Only mounts the `data/` directory
- Sets `DATABASE_URL` to point at the `db` service
- Adds `depends_on: db` so the API waits for PostgreSQL
- Activates the PostgreSQL service by clearing its profile

## Environment Variables

Pass environment variables through the `environment` key in your Compose file or by mounting a `.env` file:

```yaml
services:
  api:
    env_file:
      - ../.env
```

See [Configuration](../reference/configuration.md) for the full list of variables.

## Volumes

| Mount | Purpose |
|-------|---------|
| `./data:/app/data` | Persistent storage for SQLite database |
| `postgres_data` (named volume) | PostgreSQL data directory |
| `./:/app` (dev only) | Source code mount for live reload |

## Building the Image

```bash
docker-compose -f docker/docker-compose.yml build
```

Or directly with a version label:

```bash
docker build -f docker/Dockerfile --build-arg VERSION=v0.1.0 -t fastpki:v0.1.0 .
```

## `.dockerignore`

A `.dockerignore` file excludes `.git`, `.venv`, caches, and documentation from the build context. This keeps the context small (under 1 MB) and speeds up builds.

## Health Check

The API provides a root endpoint that can be used for health checks:

```bash
curl http://localhost:8000/
# {"message": "Welcome to FastPKI - API-based PKI management system."}
```
