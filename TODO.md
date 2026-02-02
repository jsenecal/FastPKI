# FastPKI TODO List

This document outlines the planned features and implementation steps for FastPKI, following a Test-Driven Development approach.

**Current status**: 232 tests passing, 90% coverage.

## Authentication and Authorization System

Our goal is to create a comprehensive authentication and authorization system with role-based access control, per-resource permissions, and organization-level access management.

### 1. User Authentication System

- [x] Setup project structure (FastAPI, SQLModel, tests)
- [x] Implement basic PKI functionality (CA, Certificates)
- [x] Add export functionality with TDD approach
- [x] Implement User model and authentication
  - [x] Write tests for user creation and retrieval
  - [x] Write tests for password hashing and verification
  - [x] Write tests for JWT token generation and validation
  - [x] Implement UserService with CRUD operations
  - [x] Implement AuthService for authentication
  - [x] Create login endpoint for token generation
  - [x] Add protected route dependencies

### 2. Organization and Role System

- [x] Implement Organization model
  - [x] Write tests for organization creation
  - [x] Write tests for user-organization relationships
  - [x] Write tests for role-based permissions
  - [x] Implement OrganizationService
  - [x] Update User model with organization relationship
  - [x] Add role enumeration (SUPERUSER, ADMIN, USER)
  - [x] Create organization management endpoints
  - [x] Fix organization API tests
- [x] Consolidate duplicate `get_current_user` implementations (single source of truth in `deps.py`)
- [x] Consolidate duplicate `oauth2_scheme` definitions (single definition in `deps.py`)
- [x] Use a single dependency injection pattern for database sessions (`get_session` used everywhere)

### 3. Permission System

- [x] Design and implement permission system (capability-based flags on User model instead of separate Permission table)
  - [x] Write tests for permission checking
  - [x] Write tests for permission granting/revoking
  - [x] Write tests for hierarchical permissions (user, org, role)
  - [x] Implement PermissionService
  - [x] Add permission checking dependencies
  - [x] Update CA and Certificate models with ownership fields
  - [x] Create permission management endpoints

### 4. Secure API Endpoints

- [x] Add authentication to CA endpoints
- [x] Add authentication to Certificate endpoints
- [x] Add authentication to Export endpoints
- [x] Add 401 unauthenticated access tests for CA, Certificate, and Export endpoints
- [x] Update existing endpoints with per-resource permission checks
  - [x] Write tests for CA endpoints with permission checks
  - [x] Write tests for Certificate endpoints with permission checks
  - [x] Write tests for Export endpoints with permission checks
  - [x] Refactor CA endpoints to use permissions
  - [x] Refactor Certificate endpoints to use permissions
  - [x] Refactor Export endpoints to use permissions

### 5. Audit Logging System

- [x] Implement comprehensive audit logging
  - [x] Write tests for audit log creation
  - [x] Write tests for audit log retrieval and filtering
  - [x] Design audit log schema
  - [x] Implement AuditService
  - [x] Add audit logging to all security-sensitive operations
  - [x] Create audit log query endpoints

## Security Hardening

- [x] Remove hardcoded default `SECRET_KEY` (validator rejects keys < 32 chars, warns on default value)
- [x] Replace `python-jose` with `PyJWT` (python-jose is unmaintained and has known CVEs)
- [x] Replace `passlib` with direct `bcrypt` usage (passlib incompatible with bcrypt 5.x)
- [x] Prevent double-revocation of certificates (returns 409 Conflict)
- [x] Replace f-string logging with `%s`-style formatting
- [ ] Encrypt private keys at rest in the database (CA and certificate keys are stored as plaintext PEM)

## Bug Fixes

- [x] Fix `CRLEntry.ca_id` type mismatch: guard against `cert.issuer_id is None` before creating CRLEntry
- [x] Add `model_config = {"from_attributes": True}` to `CAResponse` and `CertificateResponse` schemas
- [x] Fix `list_cas` and `list_certificates` return type: wrap with `list()`
- [x] Handle escaped commas in `parse_subject_dn` (uses `re.split(r"(?<!\\),", ...)`)
- [x] Fix JWT `exp` claim type: cast `timestamp()` float to `int` for Pydantic v2 compatibility

## Code Quality / Refactoring

- [x] Eliminate massive duplication in `app/api/organizations.py` (removed query-param endpoints, kept path-param only)
- [x] Choose one service design pattern: all services use instance-based pattern with `db` in `__init__`
- [x] Stop raising `HTTPException` in `OrganizationService`; domain exceptions in `app/services/exceptions.py`, translated to HTTP in API layer
- [x] Ensure `updated_at` is automatically managed on all models (SQLAlchemy `onupdate` handles it)
- [x] ~~Avoid generating a full RSA keypair when `include_private_key=False`~~ — Not a real issue: a keypair is required to embed the public key in the certificate; only the PEM storage is skipped

## Tech Debt

- [x] Replace deprecated `@app.on_event("startup")` with FastAPI `lifespan` context manager
- [x] Remove deprecated `default_backend()` calls from cryptography operations
- [x] Replace deprecated `sessionmaker` usage with `async_sessionmaker`
- [x] Set up Alembic migration configuration with async support and initial migration

## Implementation Notes

### Authentication Implementation Details

The authentication system uses:
- Bcrypt for password hashing (direct `bcrypt` library)
- PyJWT for JWT token encoding/decoding
- Role-based access control for coarse-grained permissions (SUPERUSER, ADMIN, USER)
- Per-user capability flags for fine-grained write permissions
- Ownership tracking via `created_by_user_id` on CA and Certificate models
- Immutable audit logging for all security-sensitive operations

### Model Structure

**User Model** (with capability flags):
```python
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True)
    hashed_password: str
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)
    organization_id: Optional[int] = Field(foreign_key="organizations.id")

    # Capability flags
    can_create_ca: bool = Field(default=False)
    can_create_cert: bool = Field(default=False)
    can_revoke_cert: bool = Field(default=False)
    can_export_private_key: bool = Field(default=False)
    can_delete_ca: bool = Field(default=False)
```

**Organization Model**:
```python
class Organization(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    # Relationships with users and resources
```

**PermissionService** (capability-based, no separate Permission table):

The PermissionService maps `PermissionAction` enums to User capability fields and enforces access via `check_ca_access()` and `check_cert_access()` methods.

### Permission Checking Logic

Permission checking follows this hierarchy:
1. Superusers have full access to everything
2. Resource creators have full access to their own resources
3. Admins have full access within their organization
4. Users can read resources within their organization
5. Users need specific capability flags for write actions

## Approach to Testing

We follow a strict TDD approach:
1. Write failing tests first
2. Implement the minimal code to make tests pass
3. Refactor while keeping tests passing

Each component of the auth system will be tested at multiple levels:
- Unit tests for services (UserService, PermissionService)
- API tests for endpoints
- Integration tests for the complete auth flow

## Next Steps

1. Encrypt private keys at rest
