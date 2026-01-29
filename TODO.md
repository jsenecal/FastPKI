# FastPKI TODO List

This document outlines the planned features and implementation steps for FastPKI, following a Test-Driven Development approach.

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
  - [ ] Fix organization API tests (3 tests failing with 404 errors)
- [ ] Consolidate duplicate `get_current_user` implementations (one in `app/api/auth.py`, another in `app/api/deps.py` with different behavior)
- [ ] Consolidate duplicate `oauth2_scheme` definitions (pointing to different URLs in `auth.py` vs `deps.py`)
- [ ] Use a single dependency injection pattern for database sessions (`get_session` vs `get_db` used inconsistently across endpoints)

### 3. Permission System

- [ ] Design and implement Permission model
  - [ ] Write tests for permission checking
  - [ ] Write tests for permission granting/revoking
  - [ ] Write tests for hierarchical permissions (user, org, role)
  - [ ] Implement PermissionService
  - [ ] Add permission checking dependencies
  - [ ] Update CA and Certificate models with ownership fields
  - [ ] Create permission management endpoints

### 4. Secure API Endpoints

- [ ] Add authentication to CA endpoints (currently completely unauthenticated)
- [ ] Add authentication to Certificate endpoints (currently completely unauthenticated)
- [ ] Add authentication to Export endpoints (private keys downloadable without auth)
- [ ] Update existing endpoints with permission checks
  - [ ] Write tests for CA endpoints with permission checks
  - [ ] Write tests for Certificate endpoints with permission checks
  - [ ] Write tests for Export endpoints with permission checks
  - [ ] Refactor CA endpoints to use permissions
  - [ ] Refactor Certificate endpoints to use permissions
  - [ ] Refactor Export endpoints to use permissions

### 5. Audit Logging System

- [ ] Implement comprehensive audit logging
  - [ ] Write tests for audit log creation
  - [ ] Write tests for audit log retrieval and filtering
  - [ ] Design audit log schema
  - [ ] Implement AuditService
  - [ ] Add audit logging to all security-sensitive operations
  - [ ] Create audit log query endpoints

## Security Hardening

- [ ] Remove hardcoded default `SECRET_KEY` (`"supersecretkey"` in `config.py`); require it to be set via environment or fail at startup
- [ ] Replace `python-jose` with `PyJWT` or `joserfc` (python-jose is unmaintained and has known CVEs)
- [ ] Encrypt private keys at rest in the database (CA and certificate keys are stored as plaintext PEM)
- [ ] Prevent double-revocation of certificates (`revoke_certificate` doesn't check current status, creating duplicate CRL entries)
- [ ] Replace f-string logging with `%s`-style formatting to avoid unnecessary evaluation and potential data leakage

## Bug Fixes

- [ ] Fix `CRLEntry.ca_id` type mismatch: field is non-nullable (`int`) but is assigned from `cert.issuer_id` which is `Optional[int]`
- [ ] Add `model_config = {"from_attributes": True}` to `CAResponse` and `CertificateResponse` schemas (required for ORM instance conversion)
- [ ] Fix `list_cas` and `list_certificates` return type: `.scalars().all()` returns `Sequence`, not `list`
- [ ] Handle escaped commas in `parse_subject_dn` (e.g., `O=Foo\, Inc.` will break the parser)

## Code Quality / Refactoring

- [ ] Eliminate massive duplication in `app/api/organizations.py` (query-param and path-param endpoint pairs are near-identical)
- [ ] Choose one service design pattern: static methods with `db` param (`CAService`) vs instance-based with `db` in `__init__` (`UserService`)
- [ ] Stop raising `HTTPException` in `OrganizationService`; raise domain exceptions and translate to HTTP in the API layer
- [ ] Ensure `updated_at` is automatically managed on all models (currently only manually set in `UserService.update_user`)
- [ ] Avoid generating a full RSA keypair when `include_private_key=False` in `CertificateService` (expensive no-op)

## Tech Debt

- [ ] Replace deprecated `@app.on_event("startup")` with FastAPI `lifespan` context manager
- [ ] Remove deprecated `default_backend()` calls from cryptography operations (no-op since cryptography 3.x)
- [ ] Replace deprecated `sessionmaker` usage with `async_sessionmaker`
- [ ] Set up Alembic migration configuration (alembic is a dependency but unused; `create_all` won't handle schema changes)

## Implementation Notes

### Authentication Implementation Details

The authentication system will use:
- Bcrypt for password hashing
- JWT tokens for authentication
- Role-based access control for coarse-grained permissions
- Per-resource permissions for fine-grained access control

### Model Structure

**User Model**:
```python
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True)
    hashed_password: str
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)

    organization_id: Optional[int] = Field(foreign_key="organizations.id")
```

**Organization Model**:
```python
class Organization(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    # Relationships with users and resources
```

**Permission Model**:
```python
class Permission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    permission_type: PermissionType
    resource_type: ResourceType
    resource_id: int

    # Target of permission (user or organization)
    user_id: Optional[int] = Field(foreign_key="users.id")
    organization_id: Optional[int] = Field(foreign_key="organizations.id")
```

### Permission Checking Logic

Permission checking will follow this hierarchy:
1. Superusers have access to everything
2. Resource owners have full access to their resources
3. Organization admins have access to all organization resources
4. Users have access based on explicitly granted permissions
5. Organization members have access based on organization permissions

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

1. Begin with user authentication tests
2. Implement user model and authentication service
3. Move to organization and permission tests
4. Gradually apply security to all endpoints
