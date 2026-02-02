# Certificates

Certificates are issued by a Certificate Authority and can be of type `server`, `client`, or `ca`.

## Issue a Certificate

Certificates are always created under a specific CA, identified by the `ca_id` query parameter.

```bash
curl -s -X POST "http://localhost:8000/api/v1/certificates/?ca_id=1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "common_name": "api.example.com",
    "subject_dn": "CN=api.example.com,O=Acme Corp,C=US",
    "certificate_type": "server",
    "key_size": 2048,
    "valid_days": 365,
    "include_private_key": true
  }' | python -m json.tool
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `common_name` | Yes | — | Common Name for the certificate |
| `subject_dn` | Yes | — | Full distinguished name |
| `certificate_type` | Yes | — | `server`, `client`, or `ca` |
| `key_size` | No | `CERT_KEY_SIZE` (2048) | RSA key size in bits |
| `valid_days` | No | `CERT_DAYS` (365) | Validity period in days |
| `include_private_key` | No | `true` | Whether to generate and store a private key |

**Required permission:** `create_cert` capability on the target CA, Admin role in the same org, or Superuser.

### Client Certificate Example

```bash
curl -s -X POST "http://localhost:8000/api/v1/certificates/?ca_id=1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "common_name": "alice",
    "subject_dn": "CN=alice,O=Acme Corp,C=US",
    "certificate_type": "client"
  }' | python -m json.tool
```

## List Certificates

```bash
# All certificates visible to the current user
curl -s http://localhost:8000/api/v1/certificates/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Filter by issuing CA
curl -s "http://localhost:8000/api/v1/certificates/?ca_id=1" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

Superusers see all certificates. Other users see only certificates belonging to their organization.

## View a Certificate

```bash
curl -s http://localhost:8000/api/v1/certificates/1 \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

## View a Certificate with Private Key

```bash
curl -s http://localhost:8000/api/v1/certificates/1/private-key \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

**Required permission:** `export_private_key` capability, Admin in the same org, or Superuser. Audit-logged.

## Revoke a Certificate

```bash
curl -s -X POST http://localhost:8000/api/v1/certificates/1/revoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Key compromise"
  }' | python -m json.tool
```

| Field | Required | Description |
|-------|----------|-------------|
| `reason` | No | Human-readable revocation reason |

The certificate status changes to `revoked` and a CRL entry is created. Revoking an already-revoked certificate returns `409 Conflict`.

**Required permission:** `revoke_cert` capability, Admin in the same org, or Superuser. Audit-logged.
