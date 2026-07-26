# Security Policy

## Supported Versions

Only the latest version on the `main` branch is actively supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

We take the security of ApexTrade Quant Server seriously. If you discover a security vulnerability, please **do not** create a public GitHub issue.

Instead, please report it privately:
1. Email details of the issue to the maintainers or open a private security advisory on GitHub.
2. Provide actionable details to help us reproduce the issue (including proof of concept if available).
3. Allow up to 48 hours for an initial response and acknowledgement.

---

## Secret & Credential Safety Guidelines

ApexTrade interacts with sensitive financial API keys (AngelOne SmartAPI, Supabase Postgres passwords, JWT secrets, etc.).

### Essential Rules:
1. **Never Commit Secrets**: Ensure `.env` is always included in `.gitignore`. Never hardcode API keys, client codes, TOTP secrets, or JWT secrets in source code files.
2. **Local AI Preference**: ApexTrade prioritizes local, offline model servers (Ollama / LiteLLM) to keep private financial data local and prevent third-party key leaks.
3. **Environment Separation**: Always use `.env.example` as a sanitized template with placeholder values.
4. **CORS & Token Guarding**: Do not relax CORS policies or remove JWT token validation on protected API endpoints.
