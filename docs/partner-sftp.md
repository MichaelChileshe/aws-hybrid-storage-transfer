# Partner deliveries: Transfer Family SFTP

Kgotla's partners deliver invoices and statements by SFTP to a server under a desk. Everyone uses one login, so every partner can see every other partner's files, and nobody patches the server. A leak of one partner's statements to another is a POPIA incident and, for a payment processor, a PCI DSS finding.

## What I built

| Piece | Setting |
|---|---|
| Server | `kgotla-partner-sftp`: SFTP only, `SERVICE_MANAGED` identities, `PUBLIC` endpoint, S3 domain, logging role attached ([`26`](screenshots/26-step10-sftp-server-and-partner-keys.png)) |
| Keys | One ed25519 key pair per partner, generated on my machine. Private keys (`-rw-------`) stay there; only the `.pub` files go to AWS |
| Users | `partner-acme`, `partner-umoya`: home directory type `LOGICAL`, one key each ([`27`](screenshots/27-step10-two-logical-users.png)) |
| Role | `hybrid-sftp-partner-role`: list and read/write under `partners/*` only |
| Session policy | [`partner-session-policy.json.tpl`](../policies/partner-session-policy.json.tpl): list and read/write only `partners/${transfer:UserName}/*` |

## Two independent locks

1. **Logical home directory.** Each user's mapping is `/` → `/<bucket>/partners/partner-<name>`. The partner's `/` *is* their folder; there's no parent directory to climb into and no bucket name to guess.
2. **Session policy.** Even if a mapping were wrong, the session policy narrows the role for that session to `partners/<their own user name>/*`. Transfer Family fills `${transfer:UserName}` at login.

Either lock alone would have stopped the cross-partner reads below. Having both means a mistake in one doesn't expose anyone.

## The tests

Test files: a 38-byte Acme invoice and a 39-byte Umoya statement ([`28`](screenshots/28-step11-partner-test-files.png)).

**Acme tries to climb out** ([`29`](screenshots/29-step11-acme-session-jailed.png)):

```
sftp> put build/acme-invoice-0001.csv
sftp> ls -l
-rwxr--r--   1        -        -       38 Oct  5 13:21 acme-invoice-0001.csv
sftp> -cd ..
sftp> pwd
Remote working directory: /
sftp> ls -l
-rwxr--r--   1        -        -       38 Oct  5 13:21 acme-invoice-0001.csv
```

`cd ..` from `/` goes nowhere. Acme sees only its own file.

**Umoya tries to read Acme's invoice** ([`30`](screenshots/30-step11-umoya-denied-and-s3-prefixes.png)):

```
sftp> put build/umoya-statement-0001.csv
sftp> ls -l
-rwxr--r--   1        -        -       39 Oct  5 13:21 umoya-statement-0001.csv
sftp> -get acme-invoice-0001.csv build/should-not-exist.csv
File "/acme-invoice-0001.csv" not found.
sftp> -get /partners/partner-acme/acme-invoice-0001.csv build/should-not-exist.csv
File "/partners/partner-acme/acme-invoice-0001.csv" not found.
```

By name and by the full bucket path: **not found** both times. To Umoya, Acme's file doesn't exist. (The leading `-` in the batch file lets the session continue after an expected failure.)

**In S3**, each delivery sits under its own prefix:

```
2026-10-05 15:21:08         38 partners/partner-acme/acme-invoice-0001.csv
2026-10-05 15:21:35         39 partners/partner-umoya/umoya-statement-0001.csv
```

(S3 listing times are my machine's local time, UTC+2; the SFTP listings are UTC.)

**Every session is on record** ([`31`](screenshots/31-step11-sftp-log-streams.png)): the log group `/aws/transfer/<server-id>` had one stream per session, `partner-acme.0359c10f59b35a643ab7` and `partner-umoya.0231a7a75555eeab58d6`.

## Something to fix before production

OpenSSH printed `WARNING: connection is not using a post-quantum key exchange algorithm` on both sessions. The server was created with Transfer Family's default security policy. Before go-live I'd choose the newest security policy Transfer Family offers (including its post-quantum key exchange options, if the partners' clients support them) and check partners can still connect.

Other production changes:

- **Endpoint:** a VPC-hosted endpoint with an Elastic IP and a security group allow-listing each partner's IP range, instead of `PUBLIC`.
- **Hostname:** a custom domain (`sftp.kgotla.co.za`) so the endpoint can change without partners reconfiguring.
- **Key rotation:** a second key per user during a change-over, then remove the old one.
- **Downstream processing:** Transfer Family managed workflows (or S3 events) to scan, validate and move files once a delivery lands.
