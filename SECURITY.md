# Security Policy

## Supported versions

Only the latest published release receives security fixes. Older versions on PyPI remain available but are not patched.

| Version | Supported |
|---|---|
| 0.1.2 | Yes |
| 0.1.1 | No |
| 0.1.0 | No — yanked |

## Reporting a vulnerability

Report privately through GitHub's security advisory form:

**https://github.com/hgus107/US-Macro-MCP/security/advisories/new**

Please do not open a public issue for a security problem. Expect an acknowledgement within seven days.

## What this server does and does not do

Understanding the attack surface makes reports more useful:

- It runs locally, launched by your MCP client as a subprocess. Nothing is hosted.
- It makes read-only HTTPS requests to `api.stlouisfed.org` and to no other host.
- It writes nothing to disk. The only state is an in-memory cache, discarded when the process exits.
- It has no write access to any file, database or API.

## Of particular interest

The one genuinely sensitive value this server handles is your `FRED_API_KEY`. The key is deliberately stripped from every log line and every error message, because MCP clients capture the server's output into their own log files.

Any path that causes the key to appear in logs, error text, tracebacks or tool responses is a real vulnerability — please report it.