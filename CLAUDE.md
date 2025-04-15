# FastPKI - Claude Guide

This file contains important information for Claude when working with this codebase.

## Project Overview

FastPKI is an API-based PKI management system that provides an easier alternative to Easy-RSA. It allows you to create and manage Certificate Authorities, issue certificates, and revoke them through a RESTful API.

## Directory Structure

- `/app`: Main application code
  - `/api`: API endpoints
  - `/core`: Core configuration
  - `/db`: Database models and session management
  - `/schemas`: Pydantic schemas for API requests/responses
  - `/services`: Business logic services
- `/tests`: Test suite
- `/docker`: Docker configuration
- `/data`: SQLite database files and other persistent data

## Development Workflow

### Essential Commands

Always run these commands before confirming code changes:

```bash
# Format code
ruff format app tests

# Check code quality and types
ruff check app tests
mypy app

# Run tests
pytest
```

### Using Make

You can use the Makefile for common operations:

```bash
# Format code
make format

# Lint and type check code
make lint

# Run tests
make test

# Run tests with coverage
make test-cov
```

## Docker Workflow

For development with Docker:

```bash
# Development mode with SQLite and code reloading
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d

# Production mode with PostgreSQL
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
```

## Type Checking Guidelines

- All function definitions should have proper type annotations
- Use appropriate types from typing module (List, Dict, Optional, etc.)
- All class attributes should be properly typed
- Use SQLModel typing conventions for database models

## Dependencies

- FastAPI for the web framework
- SQLModel for the ORM (built on SQLAlchemy)
- Cryptography for PKI operations
- Pydantic for data validation
- UV for package management
- Ruff for linting and formatting
- Mypy for type checking

## Database Configuration

The application supports both SQLite and PostgreSQL:
- Default: SQLite (`sqlite+aiosqlite:///./data/fastpki.db`)
- PostgreSQL: Configure via environment variable (`DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db`)

## Testing

- Use pytest for all tests
- Test coverage should be maintained above 80%
- Tests are in the `/tests` directory