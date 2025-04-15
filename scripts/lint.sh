#!/bin/bash
set -e

# Create directory if it doesn't exist
mkdir -p scripts

# Run formatting
echo "Running isort..."
isort app tests

echo "Running black..."
black app tests

# Run linting
echo "Running ruff..."
ruff check app tests

echo "Running mypy..."
mypy app

echo "All linting checks passed!"