# FastPKI

FastPKI is an API-based PKI management system that provides an easier alternative to Easy-RSA. It allows you to create and manage Certificate Authorities, issue certificates, and revoke them through a RESTful API.

## Features

- Create and manage Certificate Authorities (CAs)
- Issue certificates (server, client, and CA)
- Revoke certificates
- RESTful API for easy integration
- Compatible with SQLite and PostgreSQL
- Docker support for easy deployment
- Type checking with mypy
- Code quality with ruff linter and formatter

## Requirements

- Python 3.9+
- FastAPI
- SQLModel
- Cryptography
- Docker (optional)

## Quick Start

### Using Docker

The easiest way to get started is using Docker:

```bash
# Clone the repository
git clone https://github.com/jsenecal/fastpki.git
cd fastpki

# Create a .env file from the example
cp .env.example .env

# Create data directory for SQLite database
mkdir -p data

# Development mode with SQLite (recommended for local development)
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
```

For production deployments with PostgreSQL:

```bash
# Production mode with PostgreSQL
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
```

The API will be available at http://localhost:8000

### Local Development

```bash
# Clone the repository
git clone https://github.com/jsenecal/fastpki.git
cd fastpki

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies with uv (faster)
uv pip install -e ".[dev]"

# Create a .env file from the example
cp .env.example .env

# Create data directory for SQLite database
mkdir -p data

# Run the application
uvicorn app.main:app --reload
```

## Development

### Code Quality

We use the following tools to ensure code quality:

- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checker

Run linting and type checking:

```bash
# Using make
make lint

# Or directly
ruff check app tests
mypy app
```

Format code:

```bash
# Using make
make format

# Or directly
ruff format app tests
```

### Pre-commit Hooks

Install pre-commit hooks to automatically check your code before committing:

```bash
pre-commit install
```

## API Documentation

When the application is running, you can access the automatic API documentation at:

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Database Support

FastPKI supports both SQLite and PostgreSQL:

- **SQLite** (default for development):
  - Data is stored in the `data/fastpki.db` file for persistence
  - Uses the aiosqlite driver for async support
  - Connection string: `sqlite+aiosqlite:///./data/fastpki.db`

- **PostgreSQL** (recommended for production):
  - Uses the asyncpg driver for async support
  - Connection string: `postgresql+asyncpg://postgres:postgres@db:5432/fastpki`
  - Configure using the `DATABASE_URL` environment variable

## Project Structure

```
/app                # Main application code
  /api              # API endpoints
  /core             # Core configuration
  /db               # Database models and session management
  /schemas          # Pydantic schemas for API requests/responses
  /services         # Business logic services
/tests              # Test suite
/docker             # Docker configuration
/data               # SQLite database files and other persistent data
```

## Testing

Tests are written using pytest:

```bash
# Run tests (using make)
make test

# Run tests with coverage
make test-cov

# Or directly
pytest
pytest --cov=app
```

## License

[MIT License](LICENSE)