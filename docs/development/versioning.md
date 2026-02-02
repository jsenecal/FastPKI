# Versioning

FastPKI uses [Semantic Versioning](https://semver.org/) and [bumpver](https://github.com/mbarkhau/bumpver) for automated version management.

## Current Version

To display the current version:

```bash
uv run bumpver show
```

The version is defined in `pyproject.toml` and kept in sync automatically by bumpver.

## Bumping the Version

Use the Makefile targets to bump the version:

```bash
# Patch release (v0.1.0 -> v0.1.1)
make bump-patch

# Minor release (v0.1.0 -> v0.2.0)
make bump-minor

# Major release (v0.1.0 -> v1.0.0)
make bump-major
```

Each bump will:

1. Update the `version` field in `pyproject.toml` (PEP 440 format, without the `v` prefix)
2. Update `current_version` in the `[tool.bumpver]` section (with `v` prefix)
3. Create a git commit with the message `release: Bump version vX.Y.Z -> vX.Y.Z`
4. Create a git tag (e.g., `v0.2.0`)

!!! note
    Bumps do **not** push to the remote automatically. Run `git push && git push --tags` when ready.

## Configuration

The bumpver configuration lives in `pyproject.toml`:

```toml
[tool.bumpver]
current_version = "v0.1.0"
version_pattern = "vMAJOR.MINOR.PATCH"
commit_message = "release: Bump version {old_version} -> {new_version}"
commit = true
tag = true
push = false

[tool.bumpver.file_patterns]
"pyproject.toml" = [
    'version = "{pep440_version}"',
]
```

The `{pep440_version}` placeholder ensures that `pyproject.toml` contains the PEP 440 version (e.g., `0.1.0`) while git tags use the `v` prefix (e.g., `v0.1.0`).

### Adding Version to More Files

To stamp the version into additional files, add entries under `[tool.bumpver.file_patterns]`:

```toml
[tool.bumpver.file_patterns]
"pyproject.toml" = [
    'version = "{pep440_version}"',
]
"app/__init__.py" = [
    '__version__ = "{pep440_version}"',
]
```

## Docker Image Versioning

The Dockerfile accepts a `VERSION` build argument that is stored as an OCI label:

```bash
docker build -f docker/Dockerfile --build-arg VERSION=v0.1.0 -t fastpki:v0.1.0 .
```

This sets the `org.opencontainers.image.version` label on the image, which can be inspected with:

```bash
docker inspect fastpki:v0.1.0 --format '{{ index .Config.Labels "org.opencontainers.image.version" }}'
```
