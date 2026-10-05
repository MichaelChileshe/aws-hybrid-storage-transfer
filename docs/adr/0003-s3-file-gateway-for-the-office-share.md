# ADR 0003: S3 File Gateway for the office share; Tape Gateway documented, not built

**Status:** Accepted
**Context:** Staff save documents to a mounted network drive that "goes to the backup tapes". They want to keep the drive; Kgotla wants the files in S3, not on tape.

## Options considered

| Option | Verdict |
|---|---|
| Tape Gateway | ❌ For backup software that must keep writing to tape. Kgotla's users save files, they don't run a backup product against this share |
| Volume Gateway | ❌ iSCSI block storage for servers, not a file share for people |
| Ask staff to upload to S3 directly | ❌ Changes their workflow; no POSIX permissions; unlikely to happen |
| DataSync on a schedule from the old share | ❌ S3 would always lag; two copies to reason about |
| **S3 File Gateway, NFS share on `gateway/`, local cache** | ✅ Chosen |

## Decision

An S3 File Gateway on-premises with a 150 GiB cache disk exports `/kgotla-archive` over NFS, backed by `s3://…/gateway/`. Only the office subnet (`10.80.1.0/24`) can mount it, root is squashed, and the cache refreshes a folder's listing when it's older than 300 seconds.

## Consequences

- Measured: a 5 MiB file saved at 13:07:30 UTC was in S3 at 13:07:31 UTC, with its owner, group, mode and times stored as object metadata.
- Objects written to the bucket by anything else appear on the share only after a refresh. `RefreshCache` on demand made it appear (I didn't capture the listing before the refresh); `CacheStaleTimeoutInSeconds=300` handles it automatically.
- If Kgotla's backup product later needs a tape target, Tape Gateway is the addition; it doesn't replace this.
