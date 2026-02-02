# Contributing

## Development Setup

```bash
# Clone and enter the repository
git clone https://github.com/jsenecal/fastpki.git
cd fastpki

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install all dependencies including dev tools
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Code Quality

FastPKI uses the following tools to maintain code quality:

| Tool | Purpose | Command |
|------|---------|---------|
| [Ruff](https://docs.astral.sh/ruff/) | Linting and formatting | `ruff check app tests` / `ruff format app tests` |
| [mypy](https://mypy.readthedocs.io/) | Static type checking | `mypy app` |
| [pytest](https://docs.pytest.org/) | Testing | `pytest` |

### Ruff Configuration

Ruff is configured in `pyproject.toml` with the following rule sets enabled:

- `E` — pycodestyle errors
- `F` — pyflakes
- `B` — flake8-bugbear
- `C4` — flake8-comprehensions
- `I` — isort
- `N` — pep8-naming
- `UP` — pyupgrade
- `TRY` — tryceratops
- `RUF` — ruff-specific rules
- `SIM` — flake8-simplify

Line length is set to 88 characters.

### mypy Configuration

Strict mode is enabled with all `disallow_untyped_*` flags active. The SQLAlchemy mypy plugin is used for ORM type checking.

## Make Targets

| Target | Description |
|--------|-------------|
| `make install` | Install project with dev dependencies |
| `make format` | Format code with ruff |
| `make lint` | Run ruff and mypy |
| `make test` | Run pytest |
| `make test-cov` | Run pytest with coverage report |
| `make run` | Start the dev server with live reload |
| `make clean` | Remove build artifacts and caches |
| `make docs` | Build documentation with MkDocs |
| `make docs-serve` | Start MkDocs live preview server |
| `make docker-build` | Build Docker image |
| `make docker-up` | Start Docker containers |
| `make docker-down` | Stop Docker containers |
| `make bump-patch` | Bump patch version (v0.1.0 → v0.1.1) |
| `make bump-minor` | Bump minor version (v0.1.0 → v0.2.0) |
| `make bump-major` | Bump major version (v0.1.0 → v1.0.0) |

## Pre-commit Hooks

The following hooks run automatically on every commit:

1. **trailing-whitespace** — removes trailing whitespace
2. **end-of-file-fixer** — ensures files end with a newline
3. **check-yaml** — validates YAML syntax
4. **check-added-large-files** — prevents accidentally committing large files
5. **ruff** — runs the linter with auto-fix
6. **ruff-format** — formats code

## Testing

FastPKI follows Test-Driven Development (TDD) practices.

### Running Tests

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run a specific test file
pytest tests/test_ca.py -v

# Run a specific test
pytest tests/test_ca.py::test_create_ca -v
```

### Test Configuration

Tests use `pytest-asyncio` for async test support and `httpx` for testing FastAPI endpoints. Coverage is configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=app --cov-report=term-missing --cov-report=xml"
asyncio_mode = "auto"
```

### TDD Workflow

1. **Red** — Write a failing test for the new functionality
2. **Green** — Implement the minimal code to make the test pass
3. **Refactor** — Clean up while keeping tests green

## Project Structure

```
fastpki/
├── alembic/              # Database migrations
│   └── versions/         # Migration scripts
├── app/
│   ├── api/              # API route handlers
│   │   ├── auth.py       # Authentication endpoints
│   │   ├── audit.py      # Audit log endpoints
│   │   ├── ca.py         # Certificate Authority endpoints
│   │   ├── certs.py      # Certificate endpoints
│   │   ├── deps.py       # FastAPI dependencies (auth)
│   │   ├── export.py     # PEM export endpoints
│   │   ├── organizations.py
│   │   └── users.py
│   ├── core/
│   │   └── config.py     # Settings (env vars)
│   ├── db/
│   │   ├── models.py     # SQLModel database models
│   │   └── session.py    # Database engine and session
│   ├── schemas/          # Pydantic request/response schemas
│   │   ├── audit.py
│   │   ├── ca.py
│   │   ├── cert.py
│   │   ├── organization.py
│   │   └── user.py
│   ├── services/         # Business logic
│   │   ├── audit.py      # Audit logging service
│   │   ├── ca.py         # CA operations
│   │   ├── cert.py       # Certificate operations
│   │   ├── encryption.py # Private key encryption
│   │   ├── exceptions.py # Service exceptions
│   │   ├── organization.py
│   │   ├── permission.py # Permission checks
│   │   └── user.py
│   └── main.py           # FastAPI application entry point
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── docker-compose.prod.yml
├── docs/                 # MkDocs documentation
├── tests/
├── data/                 # SQLite database (gitignored)
├── mkdocs.yml
├── pyproject.toml
├── Makefile
└── .env.example
```
