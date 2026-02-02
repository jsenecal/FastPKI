# Authentication

FastPKI uses JWT (JSON Web Tokens) with OAuth2 password flow for authentication.

## Login Flow

1. **POST credentials** to the token endpoint as form-encoded data.
2. **Receive a JWT** access token in the response.
3. **Send the token** as a `Bearer` header on every subsequent request.

### Obtain a Token

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin&password=securepassword"
```

??? example "Response"

    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer"
    }
    ```

!!! note
    The token endpoint uses `application/x-www-form-urlencoded` (standard OAuth2), **not** JSON.

### Use the Token

Pass the token in the `Authorization` header:

```bash
curl -s http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### Shell Variable Shortcut

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin&password=securepassword" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Use in subsequent requests
curl -s http://localhost:8000/api/v1/cas/ \
  -H "Authorization: Bearer $TOKEN"
```

## Token Details

| Property | Value |
|----------|-------|
| Algorithm | HS256 (configurable via `ALGORITHM`) |
| Signing key | `SECRET_KEY` environment variable |
| Expiration | `ACCESS_TOKEN_EXPIRE_MINUTES` (default 1440 = 24 hours) |

### Token Payload

The JWT payload contains:

| Claim | Description |
|-------|-------------|
| `sub` | Username |
| `id` | User ID |
| `role` | User role (`superuser`, `admin`, `user`) |
| `exp` | Expiration timestamp |

## Unauthenticated Endpoints

Only two operations can be performed without a token:

1. **`POST /api/v1/auth/token`** — login
2. **`POST /api/v1/users/`** — create the first user (bootstrap) or create regular users

All other endpoints require a valid bearer token.

## Failed Login Attempts

Failed login attempts are recorded in the [audit log](../guides/audit-logs.md) with action `login_failure`, along with the attempted username. Successful logins are recorded with `login_success`.
