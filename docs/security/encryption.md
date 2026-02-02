# Encryption at Rest

FastPKI can encrypt all private keys stored in the database using [Fernet](https://cryptography.io/en/latest/fernet/) symmetric encryption. This is optional but strongly recommended for production deployments.

## How It Works

1. **Generate a Fernet key** and set it as the `PRIVATE_KEY_ENCRYPTION_KEY` environment variable.
2. **On startup**, FastPKI automatically encrypts any existing plaintext private keys in the database.
3. **New private keys** are encrypted before being stored.
4. **On read**, private keys are decrypted transparently when returned through the API.

## Setup

### Generate a Key

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

### Configure

Add the key to your `.env` file:

```bash
PRIVATE_KEY_ENCRYPTION_KEY=your-generated-fernet-key-here
```

### Startup Migration

On the next application startup, FastPKI will:

1. Scan all CA and certificate private keys in the database.
2. Encrypt any keys that are still in plaintext.
3. Verify that already-encrypted keys can be decrypted with the current key.

If the key is wrong (i.e., keys were encrypted with a different Fernet key), the application will refuse to start with an error message identifying the affected resource.

!!! warning
    **Do not lose the encryption key.** If the key is lost, encrypted private keys cannot be recovered. Store the key securely (e.g., in a secrets manager).

!!! warning
    **Do not change the key** without first decrypting all keys with the old key. There is no built-in key rotation mechanism.

## Behavior Without Encryption

If `PRIVATE_KEY_ENCRYPTION_KEY` is not set (the default), private keys are stored as plaintext PEM in the database. The API functions identically — the only difference is the storage format.

## Detection

The encryption service detects whether a stored key is encrypted or plaintext by checking if it starts with `-----BEGIN`. Fernet-encrypted data is a base64 blob that never starts with this prefix.

## Validation

The `PRIVATE_KEY_ENCRYPTION_KEY` value is validated at startup. If it is not a valid Fernet key, the application will fail to start with a clear error message including instructions for generating a valid key.
