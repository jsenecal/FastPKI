# FastPKI

**API-based PKI management system — an easier alternative to Easy-RSA.**

FastPKI lets you create and manage Certificate Authorities, issue certificates, and revoke them through a RESTful API. It is built with FastAPI, SQLModel, and the Python `cryptography` library.

## Feature Highlights

- **Certificate Authority management** — create, list, view, export, and delete CAs
- **Certificate lifecycle** — issue server and client certificates, revoke them, export PEM files and full chains
- **Multi-tenant organizations** — scope CAs and certificates to organizations with per-org user membership
- **Role-based access control** — three roles (Superuser, Admin, User) with a clear permission hierarchy
- **Per-user capability flags** — grant individual write permissions to regular users without promoting them
- **Audit logging** — immutable log of every security-sensitive action, filterable by action, user, date, and resource
- **Private key encryption at rest** — optional Fernet encryption for all stored private keys
- **Dual database support** — SQLite for development, PostgreSQL for production
- **Docker-ready** — development and production Docker Compose configurations included

## Quick Links

| Topic | Description |
|-------|-------------|
| [Installation](getting-started/installation.md) | Set up FastPKI locally or with Docker |
| [First Steps](getting-started/first-steps.md) | End-to-end walkthrough: create a superuser, login, create a CA, issue a certificate |
| [Configuration](getting-started/configuration.md) | All environment variables with types and defaults |
| [API Reference](reference/api.md) | Complete endpoint reference with methods, request bodies, and auth requirements |
| [Security](security/authentication.md) | Authentication, authorization, and encryption details |
| [Deployment](deployment/production.md) | Production deployment checklist |
