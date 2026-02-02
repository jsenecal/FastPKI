# Production Deployment

This checklist covers the key considerations for deploying FastPKI in a production environment.

## 1. Set a Strong `SECRET_KEY`

The `SECRET_KEY` is used to sign JWT tokens. The default value is insecure and will trigger a warning.

```bash
# Generate a secure random key
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Set it in your `.env` file or environment:

```bash
SECRET_KEY=your-generated-secret-key-here
```

The key must be at least 32 characters long.

## 2. Enable Private Key Encryption

Encrypt all stored private keys using Fernet encryption:

```bash
# Generate a Fernet key
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

```bash
PRIVATE_KEY_ENCRYPTION_KEY=your-fernet-key-here
```

On startup, FastPKI will automatically encrypt any existing plaintext keys. See [Encryption at Rest](../security/encryption.md).

!!! warning
    Store the encryption key securely (e.g., in a secrets manager). If lost, encrypted private keys cannot be recovered.

## 3. Use PostgreSQL

SQLite is suitable for development but not recommended for production. Switch to PostgreSQL:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/fastpki
```

Or use the production Docker Compose file which includes PostgreSQL:

```bash
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
```

## 4. Run Database Migrations

If upgrading an existing installation, run Alembic migrations:

```bash
alembic upgrade head
```

For new installations, the database tables are created automatically on startup.

## 5. Restrict CORS Origins

The default CORS setting allows all origins (`["*"]`). In production, restrict this to your frontend domain(s):

```bash
BACKEND_CORS_ORIGINS=["https://pki.example.com"]
```

## 6. Place Behind a Reverse Proxy

Run FastPKI behind a reverse proxy (nginx, Caddy, Traefik) that handles TLS termination:

```
Client → HTTPS → Reverse Proxy → HTTP → FastPKI (:8000)
```

Example nginx configuration:

```nginx
server {
    listen 443 ssl;
    server_name pki.example.com;

    ssl_certificate     /etc/ssl/certs/pki.pem;
    ssl_certificate_key /etc/ssl/private/pki.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 7. Adjust Token Expiration

The default token lifetime is 24 hours. For tighter security, reduce it:

```bash
ACCESS_TOKEN_EXPIRE_MINUTES=60  # 1 hour
```

## 8. Set Log Level

Use `INFO` or `WARNING` in production to reduce noise:

```bash
LOG_LEVEL=INFO
```

## Production Checklist

- [ ] `SECRET_KEY` set to a strong random value (>= 32 chars)
- [ ] `PRIVATE_KEY_ENCRYPTION_KEY` configured
- [ ] `DATABASE_URL` pointing to PostgreSQL
- [ ] `BACKEND_CORS_ORIGINS` restricted
- [ ] Running behind TLS-terminating reverse proxy
- [ ] `ACCESS_TOKEN_EXPIRE_MINUTES` reviewed
- [ ] Database migrations applied (`alembic upgrade head`)
- [ ] Backup strategy for database and encryption key
