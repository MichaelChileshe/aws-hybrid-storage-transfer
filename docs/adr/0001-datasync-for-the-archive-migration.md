# ADR 0001: DataSync for the archive migration, not a gateway, scripts or offline-only

**Status:** Accepted
**Context:** About 40 TB of scanned documents and ledger exports on an NFS NAS must move to S3 once, with proof that every file arrived intact, while the office keeps working on a 100 Mbps line.

## Options considered

| Option | Verdict |
|---|---|
| `aws s3 sync` from a server in the building | ❌ No managed verification report, no per-run bandwidth limit, retries and resumption are my problem |
| S3 File Gateway and copy into the share | ❌ Built for ongoing access, not bulk migration; the cache becomes the bottleneck and there's no verification step |
| Offline transfer only | ❌ Still needs a final online catch-up for files changed during shipping; only worth it if the link can't be improved |
| **DataSync agent in the building, NFS → S3, full verification** | ✅ Chosen |

## Decision

A DataSync agent on-premises reads the NAS over NFS and writes to `s3://…/migration/` through a role limited to that prefix. The task uses `VerifyMode=POINT_IN_TIME_CONSISTENT` and `TransferMode=CHANGED`, so later runs only send what changed.

## Consequences

- Measured on the sample: 2,007 files, 4.27 GB, transfer at 157.5 MB/s (1,260 Mbps), verification `SUCCESS`; S3 holds exactly 4,269,801,472 bytes.
- The agent is not the bottleneck at Kgotla's scale; the link is (see ADR 0002).
- Cost: US$0.0125 per GB copied, so about US$500 for 40 TB, plus the agent's VM.
- The agent needs a well-sized VM: AWS recommends at least 32 GiB of RAM (an m5.2xlarge on EC2), so on-premises it needs a host with room for it.
