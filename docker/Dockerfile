FROM python:3.11-slim

WORKDIR /app

# Install uv for faster dependency installation
RUN pip install uv
RUN apt-get update && apt-get install -y curl && apt-get clean

# Copy requirements and install dependencies
COPY pyproject.toml .
RUN uv pip install --no-cache-dir -e ".[dev]"

# Copy application code
COPY . .

# Run linting and type checking at build time
RUN ruff check app tests
RUN mypy app

# Create a non-root user and switch to it
RUN adduser --disabled-password --gecos "" app
USER app

# Expose the application port
EXPOSE 8000

# Run the application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]