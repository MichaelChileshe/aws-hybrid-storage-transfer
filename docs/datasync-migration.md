# Migrating the archive with DataSync

Kgotla's archive sits on a NAS in the server room: about 40 TB of scanned documents and ledger exports. It has to reach S3 complete and provably intact, and the migration must not take over the office's 100 Mbps line during the working day.

I moved a 4.27 GB sample built to look like the real thing: four large "scans" (768 MiB each) and 2,000 small "ledgers" (512 KiB each), all random data so nothing compresses on the way.

## How the pieces fit

| Piece | What it is here |
|---|---|
| **Agent** | `kgotla-datasync-agent`: an m5.2xlarge (the size AWS recommends for an agent) launched from AWS's DataSync image, found through the public SSM parameter `/aws/service/datasync/ami`. No instance role, no key pair |
| **Activation** | The agent hands out an activation key on port 80 to something on its own network. [`scripts/activation_key.py`](../scripts/activation_key.py) runs `curl` on the office PC through SSM Run Command and prints only the key. It came back after 7 s; `create-agent` registered it and it went `ONLINE` with a `PUBLIC` endpoint ([`09`](screenshots/09-step4-agent-activated-online.png)) |
| **Source location** | NFS, server `10.80.1.174`, path `/srv/archive`, read through the agent, NFS version chosen automatically |
| **Destination location** | S3 bucket, prefix `/migration`, written through `hybrid-datasync-s3-role`, which can only touch `migration/*` |
| **Task** | `kgotla-archive-migration`: `VerifyMode=POINT_IN_TIME_CONSISTENT`, `OverwriteMode=ALWAYS`, `TransferMode=CHANGED` ([`10`](screenshots/10-step5-locations-and-verified-task.png)) |

The NAS only accepts NFS (2049, 111, 20048) from the agent's security group. The office PC can't reach the archive at all.

## Run 1: no limit

[`scripts/datasync_run.py`](../scripts/datasync_run.py) `full-speed` ([`11`](screenshots/11-step5-full-speed-run-live.png), [`12`](screenshots/12-step5-full-speed-result-and-s3.png)):

| Phase | What I saw |
|---|---|
| LAUNCHING | 14:24:07 to 14:25:18 (local time), nothing moving: DataSync starting the run |
| TRANSFERRING | 1.33 GB after the first interval (111.4 MB/s), 3.32 GB after the second (167.9 MB/s = 1,343 Mbps) |
| VERIFYING | 4.27 GB moved; three polls of re-reading both sides |
| SUCCESS | 14:26:29 |

```
RESULT full-speed
  files transferred : 2,007
  bytes transferred : 4.27 GB
  phases (s)        : prepare 2  transfer 27  verify 10  total 39
  transfer rate     : 157.5 MB/s = 1260 Mbps (bytes / transfer phase)
  verification      : SUCCESS
```

S3 agreed: `Total Objects: 2007`, `Total Size: 4269801472`, which is exactly 4 × 768 MiB + 2,000 × 512 KiB. The 2,007 count is the 2,004 files plus their folders, which DataSync also copies.

**What this means for Kgotla:** one agent moved data at more than **12 times** the speed of their whole office line. Left unlimited, a migration would take every bit of that line.

## Run 2: limited to 50 Mbps

`datasync_run.py business-hours-then-night --all --mbps 50` sent everything again (`TransferMode=ALL`) with `BytesPerSecond = 6,250,000` ([`13`](screenshots/13-step6-throttled-run-50-mbps.png), [`15`](screenshots/15-step6-throttled-run-result.png)):

```
RESULT business-hours-then-night
  files transferred : 2,007
  bytes transferred : 4.27 GB
  phases (s)        : prepare 1  transfer 695  verify 10  total 706
  transfer rate     : 6.1 MB/s = 49 Mbps (bytes / transfer phase)
  verification      : SUCCESS
```

The same data took **695 s instead of 27 s**, and averaged 49 Mbps against the 50 Mbps limit. Half of Kgotla's line would stay free for card authorisations and email.

The per-interval figures are noisier than the average: most intervals show 7.8–8.2 MB/s (about 62–66 Mbps) and some show 0.0. DataSync's byte counter updates in steps, so a 10-second window can catch two updates or none. The 695-second average is the figure to plan with.

## Raising the limit mid-run: not proven

For the "night shift", the plan was to raise the limit to 200 Mbps (`BytesPerSecond=25000000`) while the run was going, using `aws datasync update-task-execution`, which exists for exactly this ([`14`](screenshots/14-step6-update-task-execution.png)). The command returned with no output and no error. **But the rates never rose**: the intervals at the end of the transfer were in the same band as at the start, and the run's average was 49 Mbps.

I didn't run `describe-task-execution` straight after the update to see the stored `Options.BytesPerSecond`, so I can't tell whether the change was never stored or stored without effect. Before I'd tell a client "you can open it up after hours", I'd repeat this and check that value first. The safe pattern that doesn't depend on it: schedule separate runs (a limited one in working hours, an unlimited one at night) with `TransferMode=CHANGED`, so each run only moves what's left.

## Takeaways

- Verification is built in: `POINT_IN_TIME_CONSISTENT` re-reads both sides and the task only reports `SUCCESS` if every file matches. That's the evidence an auditor will ask for.
- A bandwidth limit is a per-run option, so the migration plan is a schedule, not one big copy.
- The agent wasn't the bottleneck at Kgotla's scale. The link was. See [`transfer-math.md`](transfer-math.md).
