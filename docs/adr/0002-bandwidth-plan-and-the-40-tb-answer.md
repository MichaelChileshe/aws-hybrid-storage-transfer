# ADR 0002: Limit the migration in working hours, and move the bulk over a faster link

**Status:** Accepted
**Context:** The office line is 100 Mbps and carries card authorisations and email. Unlimited, one agent moved data at 1,260 Mbps on the sample, so it would take the whole line. The board asked how long 40 TB will take and whether to ship disks.

## Options considered

| Option | 40 TB takes | Verdict |
|---|---|---|
| Today's line, unlimited | 37 days, and the office has no internet | ❌ |
| Today's line, 50 Mbps limit around the clock | ~74 days | ❌ Too slow |
| **1 Gbps link (or Direct Connect) for the migration, 80% used** | **4.6 days** | ✅ Chosen for the bulk copy |
| Offline transfer (Data Transfer Terminal or partner) | shipping/handling plus copying at both ends | Fallback if the link can't be upgraded in time |

## Decision

- Until the faster link is in place, DataSync runs on the existing line with a **50 Mbps limit** in working hours.
- The bulk copy runs over the faster link.
- A final `TransferMode=CHANGED` run catches up before the cut-over.
- Limits are set per run (`BytesPerSecond`), so the plan is a schedule of runs.

## Consequences

- Measured: the 50 Mbps run moved the same 4.27 GB in 695 s at an average of 49 Mbps, verified.
- Raising the limit on a running execution with `update-task-execution` returned no error but showed no rate change in my test. Until I've confirmed it by reading back `Options.BytesPerSecond`, the plan doesn't rely on it: day and night are separate runs.
- The numbers come from [`scripts/transfer_calc.py`](../../scripts/transfer_calc.py), fed with the measured rate from the results CSV.
