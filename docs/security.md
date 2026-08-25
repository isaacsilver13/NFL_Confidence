# Security

Version: 1.0

---

# Authentication

Google OAuth only.

No passwords stored.

JWT access tokens.

Refresh tokens.

---

# Authorization

Authenticated users only.

Commissioner endpoints require OWNER role.

Users may only access their own picks.

---

# Data Protection

HTTPS only.

Environment variables for secrets.

Parameterized queries.

Input validation.

Output encoding.

---

# Rate Limiting

Authenticated

300 requests/hour

Anonymous

30 requests/hour

---

# Logging

Log

Authentication

Errors

Failed validation

Background jobs

Do Not Log

Passwords

JWTs

OAuth tokens

Secrets

---

# Security Headers

HSTS

X-Frame-Options

Content-Security-Policy

Referrer-Policy

X-Content-Type-Options

---

# Session Security

Refresh token rotation.

Secure cookies.

SameSite=Lax.

Automatic expiration.

---

# Backups

Daily PostgreSQL backups.

Encrypted.

30-day retention.

Quarterly restore testing.

---

# Dependency Management

Automated dependency updates.

Security scanning in CI.

Review high-severity vulnerabilities before release.
