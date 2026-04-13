FROM python:3.14-slim

ARG VERSION
LABEL org.opencontainers.image.version="${VERSION}"

WORKDIR /app

# Install uv for faster dependency installation
RUN pip install uv
RUN apt-get update && apt-get install -y curl && apt-get clean

# Copy files needed for dependency resolution
COPY pyproject.toml uv.lock LICENSE README.md ./
COPY cli/ cli/
COPY app/ app/

# Install dependencies (CLI + server, no dev tools)
RUN uv sync --system --no-dev --group server --no-editable

# Copy remaining application files
COPY alembic.ini ./
COPY alembic/ alembic/
COPY docker/ docker/

# Create a non-root user and switch to it
RUN adduser --disabled-password --gecos "" app
USER app

# Expose the application port
EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
