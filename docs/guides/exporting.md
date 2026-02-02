# Exporting

FastPKI provides dedicated export endpoints that return PEM files as downloads (with `Content-Disposition` headers). These are useful for scripting or directly saving files to disk.

All export endpoints require authentication.

## Export a CA Certificate

```bash
curl -s -OJ http://localhost:8000/api/v1/export/ca/1/certificate \
  -H "Authorization: Bearer $TOKEN"
# Saves: ca_1_certificate.pem
```

**Required permission:** Read access to the CA.

## Export a CA Private Key

```bash
curl -s -OJ http://localhost:8000/api/v1/export/ca/1/private-key \
  -H "Authorization: Bearer $TOKEN"
# Saves: ca_1_private_key.pem
```

**Required permission:** `export_private_key`. Audit-logged.

## Export a Certificate

```bash
curl -s -OJ http://localhost:8000/api/v1/export/certificate/1 \
  -H "Authorization: Bearer $TOKEN"
# Saves: certificate_1.pem
```

**Required permission:** Read access to the certificate.

## Export a Certificate Private Key

```bash
curl -s -OJ http://localhost:8000/api/v1/export/certificate/1/private-key \
  -H "Authorization: Bearer $TOKEN"
# Saves: certificate_1_private_key.pem
```

Returns `404` if the certificate was created without a private key (`include_private_key: false`).

**Required permission:** `export_private_key`. Audit-logged.

## Export a Certificate Chain

The chain endpoint returns the certificate followed by its issuing CA certificate, concatenated in PEM format.

```bash
curl -s -OJ http://localhost:8000/api/v1/export/certificate/1/chain \
  -H "Authorization: Bearer $TOKEN"
# Saves: certificate_1_chain.pem
```

**Required permission:** Read access to the certificate.

## Scripting Example

Retrieve a certificate and key into shell variables without saving to disk:

```bash
CERT=$(curl -s http://localhost:8000/api/v1/export/certificate/1 \
  -H "Authorization: Bearer $TOKEN")

KEY=$(curl -s http://localhost:8000/api/v1/export/certificate/1/private-key \
  -H "Authorization: Bearer $TOKEN")

echo "$CERT" > /etc/ssl/certs/myapp.pem
echo "$KEY"  > /etc/ssl/private/myapp.key
```
