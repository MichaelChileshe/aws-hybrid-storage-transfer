# The office share: S3 File Gateway

Kgotla's staff save documents to a network drive that "goes to the backup tapes". They don't want to change that habit, and Kgotla doesn't want to keep buying tapes. An S3 File Gateway gives them the same mounted share, while every file becomes an ordinary object in S3.

## Building it

| Piece | What it is here |
|---|---|
| **Appliance** | `kgotla-file-gateway`: m5.xlarge from AWS's image (`/aws/service/storagegateway/ami/FILE_S3/latest`), plus a 150 GiB gp3 disk for the cache (150 GiB is the minimum). No instance role, no key pair |
| **Activation** | Same method as the DataSync agent: the office PC asks the gateway for a key on port 80 through SSM Run Command. Key after 7 s; activated as `FILE_S3` with time zone `GMT+2:00` (Johannesburg), so maintenance runs in local time |
| **Cache** | Once the gateway reported its unallocated disk (`/dev/nvme1n1`), `add-cache` made it the local cache. The gateway then showed `RUNNING`, `FILE_S3`, `EC2`, `10.80.1.228` ([`17`](screenshots/17-step8-gateway-activated-cache-added.png)) |
| **Share** | NFS share `/kgotla-archive` on `s3://kgotla-hybrid-<account>/gateway/`, written through `hybrid-gateway-s3-role` (only `gateway/*`), clients `10.80.1.0/24`, `RootSquash`, status `AVAILABLE` ([`18`](screenshots/18-step8-nfs-share-available.png)) |

A share on a prefix needs the trailing slash on the location (`…/gateway/`) and an explicit `--file-share-name`.

The gateway's security group admits port 80 (activation) and NFS (2049, 111, 20048) from the office PC's group only. 20048 is `mountd`, which NFSv3 mounts need.

## Office saves a file: how long until it's in S3?

On the office PC, `officetool mount` found the gateway and its share through the instance role (read-only Storage Gateway describe calls) and ran `mount -t nfs -o nolock,hard 10.80.1.228:/kgotla-archive /mnt/archive` ([`19`](screenshots/19-step9-office-mounts-share.png)).

I started `scripts/wait_s3.py gateway/` on my machine, then `officetool write` on the office PC ([`20`](screenshots/20-step9-office-writes-scan.png), [`21`](screenshots/21-step9-object-in-s3-with-metadata.png)):

| Event | Time (UTC) |
|---|---|
| Office PC finished writing `scan-130730.pdf` (5 MiB, `fsync`) | 13:07:30 |
| S3 `LastModified` for `gateway/scan-130730.pdf` (5,242,880 bytes) | 13:07:31 |

So the write-back took **about one second**, at the one-second resolution these timestamps allow. (The watcher's "appeared after 25 s of watching" counts from when I started it, not from the write.)

The gateway stores the file's POSIX details as object metadata, so the share can show them again later:

| Metadata | Value | Meaning |
|---|---|---|
| `user-agent` / `user-agent-id` | `aws-storage-gateway` / `sgw-ADBB6BC5` | Written by this gateway |
| `file-owner`, `file-group` | `65534` | `nobody`: root on the office PC was squashed |
| `file-permissions` | `0644` | The file's mode |
| `file-mtime`, `file-ctime` | `1791205650105000000ns` | 2026-10-05 13:07:30 UTC, the write time |

On the share, `ls` showed `scan-130730.pdf` owned by `nobody nobody` ([`22`](screenshots/22-step9-share-shows-scan-root-squashed.png)). That's **RootSquash** working: being root on a client machine doesn't make you root on the archive.

## The cache trap

A File Gateway knows about the objects it wrote. Objects that arrive in the bucket some other way (a finance system writing straight to S3, say) aren't on the share until the gateway refreshes its view.

1. Before: the share listed only `scan-130730.pdf` ([`22`](screenshots/22-step9-share-shows-scan-root-squashed.png)).
2. I uploaded `direct-to-s3.txt` (71 bytes) straight to `s3://…/gateway/` ([`23`](screenshots/23-step9-direct-upload-refresh-cache-auto-refresh.png)).
3. `aws storagegateway refresh-cache` returned notification `a2af2df7-335f-483c-bbed-c4670ff0a951`.
4. After: the share listed `direct-to-s3.txt` (`rw-rw-rw-`, `nobody`) next to the scan ([`24`](screenshots/24-step9-direct-object-visible-after-refresh.png)).

I didn't capture a listing between steps 2 and 3, so the screenshots show "before" and "after refresh", not the moment it was missing. The behaviour is documented by AWS and it's the reason for the fix below.

**The production fix:** `update-nfs-file-share --cache-attributes CacheStaleTimeoutInSeconds=300` ([`25`](screenshots/25-step9-cache-stale-timeout-300.png)). When someone lists a folder whose cached view is older than five minutes, the gateway refreshes it from S3 first. For anything that must appear immediately, the writer should go through the gateway, or call `RefreshCache` after writing (an S3 event can trigger that).

## Why File Gateway and not the other gateway types

| Gateway type | Fits when | For Kgotla |
|---|---|---|
| **S3 File Gateway** | Apps and people save files to an NFS/SMB share; the data should be S3 objects | ✅ The office share |
| Tape Gateway | Backup software must keep writing to (virtual) tape, archived to S3 / Glacier | Only if Kgotla's backup product stays; documented, not built |
| Volume Gateway | Servers need iSCSI block volumes backed by S3 snapshots | No block workload here |
| FSx File Gateway | Local cache in front of FSx for Windows | AWS has stopped offering it to new customers; Kgotla's FSx is reached over the network instead |
