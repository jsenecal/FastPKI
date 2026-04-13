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
| `parent_ca_id` | No | `null` | ID of parent CA (creates an intermediate CA) |
| `path_length` | No | `null` | BasicConstraints path length (limits sub-CA depth) |
| `allow_leaf_certs` | No | `null` | Whether this CA can issue leaf certificates (auto-managed) |
| `crl_base_url` | No | `null` | Override base URL for CDP/AIA extensions in issued certificates. Defaults to the request domain. |

The response is a `CADetailResponse` that includes the private key. This is the only time the private key is returned automatically — subsequent reads require explicit private key access.

**Required permission:** `create_ca` capability, Admin role in the same org, or Superuser.

## Intermediate CAs

FastPKI supports a full CA hierarchy. Create an intermediate CA by specifying a `parent_ca_id`:

```bash
curl -s -X POST http://localhost:8000/api/v1/cas/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Issuing CA",
    "subject_dn": "CN=Issuing CA,O=Acme Corp,C=US",
    "key_size": 4096,
    "valid_days": 1825,
    "parent_ca_id": 1
  }' | python -m json.tool
```

### Path Length Constraints

Use `path_length` to limit how deep the CA hierarchy can go. A CA with `path_length=0` can issue leaf certificates but cannot create sub-CAs. The path length auto-decrements: if a parent has `path_length=2`, its child defaults to `path_length=1`.

### Leaf Certificate Policy (`allow_leaf_certs`)

When you create an intermediate CA under a parent, the parent's `allow_leaf_certs` is automatically set to `False`. This prevents issuing leaf certificates directly from a CA that has delegated signing to intermediates. Attempting to issue a leaf certificate from such a CA returns a `400` error.

You can override this behavior by explicitly setting `allow_leaf_certs` when creating a CA:

```json
{
  "name": "Dual-Purpose CA",
  "subject_dn": "CN=Dual CA,O=Acme Corp,C=US",
  "allow_leaf_certs": true
}
```

### View CA Chain

Retrieve the full certificate chain from a CA up to the root:

```bash
curl -s http://localhost:8000/api/v1/cas/2/chain \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

Returns an ordered array starting with the specified CA and ending at the root.

### View Child CAs

List direct children of a CA:

```bash
curl -s http://localhost:8000/api/v1/cas/1/children \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

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

Returns `204 No Content` on success. Deleting a CA also deletes all certificates it has issued (cascade). A CA that has child CAs cannot be deleted — returns `409 Conflict`.

**Required permission:** `delete_ca` capability, Admin role in the same org, or Superuser. Audit-logged.
