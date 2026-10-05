# ADR 0006: One role per service, scoped to its own prefix, with aws:SourceAccount

**Status:** Accepted
**Context:** Three AWS services write into one bucket on Kgotla's behalf, and each needs an IAM role it can assume. A role that any service principal can assume, from any account, invites the confused-deputy problem.

## Options considered

| Option | Verdict |
|---|---|
| One role for all three services, full bucket access | ❌ A mistake in one service's configuration could overwrite another's data |
| Separate buckets per service | ❌ Workable, but triples bucket policies, logging and lifecycle for no extra isolation over prefix-scoped roles |
| **One role per service, each limited to its own prefix, `aws:SourceAccount` on every trust policy** | ✅ Chosen |

## Decision

| Role | Trusted service | Can write |
|---|---|---|
| `hybrid-datasync-s3-role` | `datasync.amazonaws.com` | `migration/*` |
| `hybrid-gateway-s3-role` | `storagegateway.amazonaws.com` | `gateway/*` |
| `hybrid-sftp-partner-role` | `transfer.amazonaws.com` | `partners/*`, narrowed per session to `partners/${transfer:UserName}/*` |
| `hybrid-sftp-logging-role` | `transfer.amazonaws.com` | CloudWatch Logs only (`AWSTransferLoggingAccess`) |
| `hybrid-office-role` (office PC and NAS) | `ec2.amazonaws.com` | Nothing in S3: read-only Storage Gateway describe calls + SSM for Session Manager |

Every service trust policy has `"Condition": {"StringEquals": {"aws:SourceAccount": "<account>"}}`, filled at run time from a template so no account ID is committed.

## Consequences

- Another account's DataSync, Storage Gateway or Transfer Family can't use these roles even if it learns their ARNs.
- Each prefix has exactly one writer, which makes the bucket's contents easy to audit.
- The bucket blocks all public access (all four settings `True`).
- No `Deny` statements, so the account administrator can always clean up.
