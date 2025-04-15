#!/bin/bash
set -e

# Create directory if it doesn't exist
mkdir -p scripts

# Run formatting and linting
echo "Running ruff format..."
ruff format app tests

echo "Running ruff check..."
ruff check app tests

echo "Running mypy..."
mypy app

echo "All linting checks passed!"