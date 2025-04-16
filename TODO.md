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

- [ ] Implement Organization model
  - [ ] Write tests for organization creation
  - [ ] Write tests for user-organization relationships
  - [ ] Write tests for role-based permissions
  - [ ] Implement OrganizationService
  - [ ] Update User model with organization relationship
  - [ ] Add role enumeration (SUPERUSER, ADMIN, USER)
  - [ ] Create organization management endpoints

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