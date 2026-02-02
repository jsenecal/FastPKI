# Certificate Authorities

Certificate Authorities (CAs) are the trust anchors of your PKI. Every certificate issued by FastPKI is signed by a CA.

## Create a CA

```bash
curl -s -X POST http://localhost:8000/api/v1/cas/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Root CA",
    "subject_dn": "CN=Production Root CA,O=Acme Corp,C=US",
    "description": "Root CA for production services",
    "key_size": 4096,
    "valid_days": 3650
  }' | python -m json.tool
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `name` | Yes | — | Human-readable name for the CA |
| `subject_dn` | Yes | — | X.509 distinguished name (e.g. `CN=...,O=...,C=...`) |
| `description` | No | `null` | Optional description |
| `key_size` | No | `CA_KEY_SIZE` (4096) | RSA key size in bits |
| `valid_days` | No | `CA_CERT_DAYS` (3650) | Certificate validity in days |

The response is a `CADetailResponse` that includes the private key. This is the only time the private key is returned automatically — subsequent reads require explicit private key access.

**Required permission:** `create_ca` capability, Admin role in the same org, or Superuser.

## List CAs

```bash
curl -s http://localhost:8000/api/v1/cas/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

Superusers see all CAs. Other users see only CAs belonging to their organization.

## View a Single CA

```bash
curl -s http://localhost:8000/api/v1/cas/1 \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

The response does **not** include the private key.

## View a CA with Private Key

```bash
curl -s http://localhost:8000/api/v1/cas/1/private-key \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

**Required permission:** `export_private_key` capability, Admin role in the same org, or Superuser. This action is recorded in the audit log.

## Export CA Certificate (PEM download)

```bash
curl -s -OJ http://localhost:8000/api/v1/export/ca/1/certificate \
  -H "Authorization: Bearer $TOKEN"
```

Downloads `ca_1_certificate.pem`.

## Export CA Private Key (PEM download)

```bash
curl -s -OJ http://localhost:8000/api/v1/export/ca/1/private-key \
  -H "Authorization: Bearer $TOKEN"
```

Downloads `ca_1_private_key.pem`. Requires `export_private_key` permission. Audit-logged.

## Delete a CA

```bash
curl -s -X DELETE http://localhost:8000/api/v1/cas/1 \
  -H "Authorization: Bearer $TOKEN"
```

Returns `204 No Content` on success. Deleting a CA also deletes all certificates it has issued (cascade).

**Required permission:** `delete_ca` capability, Admin role in the same org, or Superuser. Audit-logged.
