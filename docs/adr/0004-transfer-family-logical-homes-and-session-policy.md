# ADR 0004: Transfer Family with logical home directories and a session policy per user

**Status:** Accepted
**Context:** Partners deliver files by SFTP to a server under a desk with one shared login, so every partner sees every other partner's files. Partners won't change their tools.

## Options considered

| Option | Verdict |
|---|---|
| Keep the desk-side server, add accounts | ❌ Still a server to patch and secure; still in the building that's being emptied |
| SFTP server on EC2 | ❌ Same patching and hardening work, now in AWS |
| Transfer Family with `PATH` home directories | ❌ Partners would see real bucket paths; isolation relies on the role alone |
| **Transfer Family, service-managed users, `LOGICAL` home + session policy** | ✅ Chosen |

## Decision

- One Transfer Family SFTP server backed by S3.
- One user per partner, each with their own SSH key.
- Each user's `/` is mapped to `partners/partner-<name>/`.
- A shared role allows `partners/*`; a session policy narrows each session to `partners/${transfer:UserName}/*`.
- A logging role sends every session to CloudWatch Logs.

## Consequences

- Measured: Acme's `cd ..` left it at `/`; Umoya's two attempts to fetch Acme's invoice (by name and by full path) both returned "not found"; each file landed under its own prefix; one log stream per session.
- Two independent locks: a mistake in one doesn't expose anyone.
- About US$216 a month per protocol endpoint while it exists, plus US$0.04/GB.
- Before production: VPC-hosted endpoint with an IP allow-list, a custom hostname, and a newer security policy (OpenSSH warned that the key exchange wasn't post-quantum).
