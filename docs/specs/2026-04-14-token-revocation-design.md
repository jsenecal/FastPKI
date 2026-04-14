# Token Revocation & Refresh Tokens

## Problem

JWT access tokens have a 24-hour expiry with no revocation mechanism. Compromised tokens cannot be invalidated. Users who are deactivated or have role/password changes still hold valid tokens until natural expiry. See issue #10.

## Design

### Token Lifecycle

- Access token TTL: 15 minutes (changed from 24 hours)
- Refresh token TTL: 24 hours
- Access tokens are JWTs with a `jti` (UUID) and `iat` (issued-at) claim
- Refresh tokens are opaque random strings stored in the database
- On refresh, the old refresh token is revoked and a new pair is issued (rotation)

### Database Changes

#### New table: `blocklisted_token`

| Column | Type        | Notes                              |
|--------|-------------|------------------------------------|
| id     | int (PK)    |                                    |
| jti    | str (unique, indexed) | JWT ID from the access token |
| exp    | datetime    | Copied from the token; used for GC |

#### New table: `refresh_token`

| Column     | Type              | Notes                        |
|------------|-------------------|------------------------------|
| id         | int (PK)          |                              |
| token      | str (unique, indexed) | Opaque random string     |
| user_id    | int (FK → User)   |                              |
| expires_at | datetime          |                              |
| revoked    | bool              | Default False                |
| created_at | datetime          |                              |

#### Modified model: `User`

| Column               | Type          | Notes                                         |
|----------------------|---------------|-----------------------------------------------|
| tokens_invalidated_at | datetime NULL | When set, reject access tokens with `iat` before this value |

### New Endpoints

#### `POST /api/v1/auth/refresh`

- Request body: `{"refresh_token": "..."}`
- Validates the refresh token exists, is not revoked, and is not expired
- Revokes the old refresh token
- Issues a new access token + refresh token pair
- Response: `{"access_token": "...", "refresh_token": "...", "token_type": "bearer"}`
- No authentication header required (the refresh token is the credential)

#### `POST /api/v1/auth/logout`

- Requires authentication (Bearer token)
- Blocklists the current access token by its `jti`
- Revokes the refresh token associated with the session (passed in request body: `{"refresh_token": "..."}`)
- Response: `204 No Content`

#### `POST /api/v1/auth/invalidate`

- Requires authentication (Bearer token)
- Sets `user.tokens_invalidated_at = now()` — all access tokens with `iat` before this are rejected
- Revokes all refresh tokens for the current user
- Response: `204 No Content`

### Auth Flow Changes

#### Token creation

- `create_access_token` adds `jti` (UUID4) and `iat` (current timestamp) claims to every JWT
- Login returns `{"access_token": "...", "refresh_token": "...", "token_type": "bearer"}`

#### Token validation (`get_current_user`)

Two additional checks before accepting an access token:

1. Reject if `jti` exists in the `blocklisted_token` table
2. Reject if `user.tokens_invalidated_at` is set and `iat < tokens_invalidated_at`

#### Automatic revocation triggers

- On password change: set `tokens_invalidated_at = now()`, revoke all refresh tokens
- On user deactivation: set `tokens_invalidated_at = now()`, revoke all refresh tokens

### Garbage Collection

Background asyncio task registered in FastAPI lifespan:

- Runs every hour
- Deletes `blocklisted_token` rows where `exp < now()`
- Deletes `refresh_token` rows where `expires_at < now()`

### Configuration

| Variable                      | Default | Description                    |
|-------------------------------|---------|--------------------------------|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 15      | Access token lifetime          |
| `REFRESH_TOKEN_EXPIRE_MINUTES`| 1440    | Refresh token lifetime (24h)   |

### Migration

- Alembic migration to add `blocklisted_token` table, `refresh_token` table, and `tokens_invalidated_at` column on `user`
- Default value of `ACCESS_TOKEN_EXPIRE_MINUTES` changes from 1440 to 15

### Updated Response Schema

The `Token` schema changes from:

```json
{"access_token": "...", "token_type": "bearer"}
```

To:

```json
{"access_token": "...", "refresh_token": "...", "token_type": "bearer"}
```
