FROM python:3.11-slim

WORKDIR /app

# Install uv for faster dependency installation
RUN pip install uv
RUN apt-get update && apt-get install -y curl && apt-get clean

# First copy files needed for installation
COPY pyproject.toml LICENSE README.md ./

# Install dependencies (without dev dependencies for the main image)
RUN uv pip install --system --no-cache-dir -e .

# Now copy the rest of the application code
COPY . .

# Create a non-root user and switch to it
RUN adduser --disabled-password --gecos "" app
USER app

# Expose the application port
EXPOSE 8000

# Run the application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]