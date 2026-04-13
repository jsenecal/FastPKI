# CRL & Public PKI Endpoints

FastPKI provides public (unauthenticated) endpoints for downloading CRLs and CA certificates. These URLs are also embedded as x509 extensions in issued certificates.

## Public endpoints

These endpoints are mounted at the application root, not under `/api/v1/`. They require no authentication.

### URL format

All public URLs use a slug format: `{name-slug}-{id}`

For a CA named "My Root CA" with ID 3, the slug is `my-root-ca-3`.

!!! note "Anti-enumeration"
    The full slug is validated — both the name prefix and the ID must match. Requesting `/crl/wrong-name-3` returns 404 even if CA 3 exists.

### CRL download

```bash
# DER format (default for PKI clients)
curl -O https://pki.example.com/crl/my-root-ca-3

# PEM format
curl -O https://pki.example.com/crl/my-root-ca-3.pem
```

| Path | Content-Type | Format |
|------|-------------|--------|
| `/crl/{slug}` | `application/pkix-crl` | DER |
| `/crl/{slug}.pem` | `application/x-pem-file` | PEM |

### CA certificate download

```bash
# DER format
curl -O https://pki.example.com/ca/my-root-ca-3.crt

# PEM format
curl -O https://pki.example.com/ca/my-root-ca-3.pem
```

| Path | Content-Type | Format |
|------|-------------|--------|
| `/ca/{slug}.crt` | `application/pkix-cert` | DER |
| `/ca/{slug}.pem` | `application/x-pem-file` | PEM |

## CDP and AIA extensions

When certificates are issued, FastPKI automatically embeds two x509 extensions pointing to the issuing CA's public endpoints:

- **CRL Distribution Point (CDP)** — where clients fetch the CRL to check revocation
- **Authority Information Access (AIA)** — where clients fetch the issuing CA's certificate

These extensions use the request's base URL by default. For example, if you create a certificate via `https://pki.example.com/api/v1/certificates/`, the embedded URLs will be:

```
CRL Distribution Point: https://pki.example.com/crl/my-root-ca-3
CA Issuers:             https://pki.example.com/ca/my-root-ca-3.crt
```

Intermediate CA certificates also include these extensions, pointing to the parent CA's endpoints.

### Per-CA base URL override

Each CA has an optional `crl_base_url` field. When set, it overrides the request domain for CDP/AIA URLs embedded in certificates issued by that CA.

```bash
# Create a CA with a custom base URL for CDP/AIA
curl -X POST https://localhost:8000/api/v1/cas/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production CA",
    "subject_dn": "CN=Production CA,O=Acme",
    "crl_base_url": "https://pki.acme.com"
  }'
```

Certificates issued by this CA will embed `https://pki.acme.com/crl/production-ca-1` instead of the request domain.

## CRL content

The CRL is generated on each request and contains the serial numbers of all certificates revoked under that CA. To revoke a certificate:

```bash
curl -X POST https://pki.example.com/api/v1/certificates/5/revoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "key compromise"}'
```

After revocation, the certificate's serial number appears in the CA's CRL.

## Verifying with OpenSSL

```bash
# Download the CRL and CA certificate
curl -o ca.crt https://pki.example.com/ca/my-root-ca-3.crt
curl -o ca.crl https://pki.example.com/crl/my-root-ca-3

# Inspect the CRL
openssl crl -in ca.crl -inform DER -text -noout

# Verify a certificate against the CRL
openssl verify -crl_check -CRLfile ca.crl -CAfile ca.pem server.pem
```
