# Models Reference

This page documents the database models and enumerations used by FastPKI.

## Enumerations

### `UserRole`

| Value | Description |
|-------|-------------|
| `superuser` | Global admin — full access to everything |
| `admin` | Organization admin — full access within their organization |
| `user` | Regular user — read access plus capability-gated write actions |

### `CertificateType`

| Value | Description |
|-------|-------------|
| `ca` | CA certificate |
| `server` | Server / TLS certificate |
| `client` | Client certificate |

### `CertificateStatus`

| Value | Description |
|-------|-------------|
| `valid` | Active certificate |
| `revoked` | Certificate has been revoked |
| `expired` | Certificate has passed its `not_after` date |

### `PermissionAction`

| Value | Description |
|-------|-------------|
| `read` | View a resource |
| `create_ca` | Create a Certificate Authority |
| `create_cert` | Issue a certificate |
| `revoke_cert` | Revoke a certificate |
| `export_private_key` | View or download a private key |
| `delete_ca` | Delete a Certificate Authority |

### `AuditAction`

| Value | Description |
|-------|-------------|
| `ca_create` | CA created |
| `ca_delete` | CA deleted |
| `ca_export_private_key` | CA private key viewed / exported |
| `cert_create` | Certificate issued |
| `cert_revoke` | Certificate revoked |
| `cert_export_private_key` | Certificate private key viewed / exported |
| `login_success` | Successful login |
| `login_failure` | Failed login attempt |
| `user_create` | User created |
| `user_update` | User updated |
| `org_create` | Organization created |
| `org_delete` | Organization deleted |
| `org_add_user` | User added to organization |
| `org_remove_user` | User removed from organization |

## Database Models

### `Organization`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `int` | Primary key | Auto-increment ID |
| `name` | `str` | Unique, indexed | Organization name |
| `description` | `str` | Nullable | Optional description |
| `created_at` | `datetime` | — | Creation timestamp (UTC) |
| `updated_at` | `datetime` | — | Last update timestamp (UTC) |

### `User`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `int` | Primary key | Auto-increment ID |
| `username` | `str` | Unique, indexed | Login username |
| `email` | `str` | Unique, indexed | Email address |
| `hashed_password` | `str` | — | bcrypt password hash |
| `role` | `UserRole` | — | User role |
| `is_active` | `bool` | Default `true` | Whether the user can authenticate |
| `can_create_ca` | `bool` | Default `false` | Capability flag |
| `can_create_cert` | `bool` | Default `false` | Capability flag |
| `can_revoke_cert` | `bool` | Default `false` | Capability flag |
| `can_export_private_key` | `bool` | Default `false` | Capability flag |
| `can_delete_ca` | `bool` | Default `false` | Capability flag |
| `organization_id` | `int` | FK → `organizations.id`, nullable | Organization membership |
| `created_at` | `datetime` | — | Creation timestamp (UTC) |
| `updated_at` | `datetime` | — | Last update timestamp (UTC) |

### `CertificateAuthority`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `int` | Primary key | Auto-increment ID |
| `name` | `str` | Indexed | CA name |
| `description` | `str` | Nullable | Optional description |
| `subject_dn` | `str` | — | X.509 distinguished name |
| `key_size` | `int` | — | RSA key size |
| `valid_days` | `int` | — | Certificate validity period |
| `private_key` | `str` | — | PEM-encoded private key (may be Fernet-encrypted) |
| `certificate` | `str` | — | PEM-encoded certificate |
| `organization_id` | `int` | FK → `organizations.id`, nullable | Owning organization |
| `created_by_user_id` | `int` | FK → `users.id`, nullable | Creating user |
| `parent_ca_id` | `int` | FK → `certificate_authorities.id`, nullable | Parent CA (null for root CAs) |
| `path_length` | `int` | Nullable | BasicConstraints path length constraint |
| `allow_leaf_certs` | `bool` | Default `true` | Whether this CA can issue leaf certificates |
| `created_at` | `datetime` | — | Creation timestamp (UTC) |
| `updated_at` | `datetime` | — | Last update timestamp (UTC) |

**Relationships:** A CA can have one `parent_ca` and many `child_cas`, forming a hierarchy.

### `Certificate`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `int` | Primary key | Auto-increment ID |
| `common_name` | `str` | Indexed | Certificate common name |
| `subject_dn` | `str` | — | Full distinguished name |
| `certificate_type` | `CertificateType` | — | `server`, `client`, or `ca` |
| `key_size` | `int` | — | RSA key size |
| `valid_days` | `int` | — | Validity period |
| `status` | `CertificateStatus` | Default `valid` | Current status |
| `private_key` | `str` | Nullable | PEM-encoded private key (may be encrypted) |
| `certificate` | `str` | — | PEM-encoded certificate |
| `serial_number` | `str` | Indexed | Certificate serial number |
| `not_before` | `datetime` | — | Validity start |
| `not_after` | `datetime` | — | Validity end |
| `revoked_at` | `datetime` | Nullable | Revocation timestamp |
| `issuer_id` | `int` | FK → `certificate_authorities.id`, nullable | Issuing CA |
| `organization_id` | `int` | FK → `organizations.id`, nullable | Owning organization |
| `created_by_user_id` | `int` | FK → `users.id`, nullable | Creating user |
| `created_at` | `datetime` | — | Creation timestamp (UTC) |
| `updated_at` | `datetime` | — | Last update timestamp (UTC) |

### `CRLEntry`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `int` | Primary key | Auto-increment ID |
| `serial_number` | `str` | Indexed | Revoked certificate serial number |
| `revocation_date` | `datetime` | — | When the certificate was revoked |
| `reason` | `str` | Nullable | Revocation reason |
| `ca_id` | `int` | FK → `certificate_authorities.id` | CA that issued the revoked certificate |
| `created_at` | `datetime` | — | Entry creation timestamp (UTC) |

### `AuditLog`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `int` | Primary key | Auto-increment ID |
| `created_at` | `datetime` | Indexed | Event timestamp (UTC) |
| `action` | `AuditAction` | Indexed | Type of action |
| `user_id` | `int` | FK → `users.id`, indexed, nullable | User who performed the action |
| `username` | `str` | Nullable | Username at the time of the action |
| `organization_id` | `int` | FK → `organizations.id`, indexed, nullable | Organization context |
| `resource_type` | `str` | Nullable | Type of affected resource |
| `resource_id` | `int` | Nullable | ID of affected resource |
| `detail` | `str` | Nullable | Human-readable description |
