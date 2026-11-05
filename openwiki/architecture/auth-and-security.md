---
type: architecture
title: Authentication and Security
description: How Mealie authenticates users (credentials, LDAP, OIDC, reverse proxy), mints and validates JWTs and API tokens, resolves the current user as a FastAPI dependency, and locks out repeated failed logins.
tags: [auth, jwt, ldap, oidc, security]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-04T19:23:01.839Z
sources:
  - id: openwiki-source-95a25fd715a3d802ff8d3349
    resource: repo://mealie/core/dependencies/dependencies.py
  - id: openwiki-source-b32b660d34270b2848ba6c37
    resource: repo://mealie/core/security/providers/credentials_provider.py
  - id: openwiki-source-79e9e9da0a3a7ec85cfab611
    resource: repo://mealie/core/security/providers/ldap_provider.py
  - id: openwiki-source-4a5604c0eca1df7b6ef06032
    resource: repo://mealie/core/security/providers/reverse_proxy_provider.py
  - id: openwiki-source-b158d084e5064882d2597bf5
    resource: repo://mealie/core/security/security.py
  - id: openwiki-source-8f8397d49bbf17a8567d236c
    resource: repo://mealie/core/security/tokens.py
  - id: openwiki-source-f361353a42c16c85b832890d
    resource: repo://mealie/services/user_services/user_service.py
generated: { by: "claude-code", at: "2026-11-04T19:23:01.839Z" }
---

# Authentication and Security

## Auth providers

All login mechanisms subclass `AuthProvider` (`mealie/core/security/providers/auth_provider.py`), which holds the DB session, request data and an abstract `authenticate()` returning `(token, lifetime)` or `None`. The base class also supplies `try_get_user` (look up by username, then email, case-insensitively) and `get_access_token`.

| Provider | Behavior |
| --- | --- |
| `CredentialsProvider` | Local username/password. Only for users whose `auth_method` is `MEALIE`. |
| `LDAPProvider` | Extends `CredentialsProvider`. If the user is unknown or has `auth_method == LDAP`, it tries LDAP (creating the user if needed); otherwise it falls through to local credentials. |
| `OpenIDProvider` | OIDC login from `UserInfo` claims; also fetches and caps profile pictures from the claim, with scheme and host allow-listing. |
| `ReverseProxyProvider` | Trusts a username forwarded by a proxy header; can auto-create users when `REVERSE_PROXY_AUTH_SIGNUP_ENABLED`. |

`get_auth_provider` in `security.py` picks `LDAPProvider` when `LDAP_ENABLED`, else `CredentialsProvider`. OIDC and reverse-proxy logins are handled by dedicated routes in `mealie/routes/auth/auth.py` (`oauth_login`, `oauth_callback`, native OIDC config/token endpoints, `reverse_proxy_login`, plus `refresh_token` and `logout`).

## Brute-force protection

`CredentialsProvider.authenticate` increments `login_attemps` on a bad password and, at `SECURITY_MAX_LOGIN_ATTEMPTS`, calls `UserService.lock_user` (sets `locked_at`). A locked user raises `UserLockedOut`. A successful login resets the counter. Unknown users and non-Mealie users still run a dummy password verify so response time does not reveal whether the account exists. The hourly `locked_user_reset` scheduler task calls `UserService.reset_locked_users`, which unlocks users whose lock has expired (see [[app-lifecycle]]).

## Tokens

`create_access_token` (`mealie/core/security/tokens.py`) signs an HS256 JWT with `settings.SECRET`, adding `iss=mealie`, `iat` and `exp` (default `TOKEN_TIME` hours). It returns the lifetime so clients know when to refresh. The `remember_me` flag is carried as the `rme` claim and only affects whether the client persists the token, not its validity. Short-lived (30 min) file tokens for downloads are made by `create_file_token`. `url_safe_token` generates opaque tokens for invitations and password resets.

## Resolving the current user

`mealie/core/dependencies/dependencies.py` provides the FastAPI dependencies used by controllers (see [[backend-layers]]):

- `get_auth_token` reads the bearer token from the `Authorization` header, falling back to the `mealie.access_token` cookie.
- `get_current_user` decodes the JWT. If it carries a `long_token` claim it is treated as an API token and validated against the `api_tokens` repository (`validate_long_live_token`); otherwise it loads the user by `sub`. It commits the session right after reading to avoid idle-in-transaction connections.
- Password changes invalidate earlier tokens: if the user's `tokens_valid_after` is set, tokens whose `iat` is missing or older are rejected.
- `try_get_current_user` returns `None` instead of raising; `get_admin_user` raises 403 for non-admins; `get_integration_id` extracts the `integration_id` claim.

User-facing consequences for data access are covered in [[multi-tenancy]]; the frontend side of login state is in [[frontend]].
