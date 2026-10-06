# Cost model

## What this build cost (estimate)

The DataSync agent, the File Gateway and the SFTP endpoint all bill **by the hour while they exist**, so the build was planned to finish and tear down in one sitting.

| Item | Rate (us-east-1 list price, approx.) | Time alive | Approx. cost |
|---|---|---|---|
| DataSync agent, m5.2xlarge (the size AWS recommends for an agent) | ~US$0.38/hour | ~2.5 hours | ~US$0.96 |
| File Gateway, m5.xlarge + 150 GiB gp3 cache | ~US$0.21/hour | ~2 hours | ~US$0.42 |
| Transfer Family SFTP endpoint | US$0.30/hour + US$0.04/GB uploaded or downloaded | ~1 hour | ~US$0.30 |
| NAS (t3.small, 20 GiB) + office PC (t3.micro) | ~US$0.03/hour together | ~2.5 hours | ~US$0.08 |
| DataSync copying | US$0.0125/GB | ~8.5 GB over two runs | ~US$0.11 |
| S3 (~8.5 GB for a few hours), CloudWatch Logs, requests | – | – | cents |
| **Total** | | | **about US$2–4** |

Rates are approximate list prices; check the pricing pages for current figures. Storage Gateway on EC2 has no gateway fee of its own: you pay for the instance, the cache disk, and S3. Cost Explorer refreshes at least once every 24 hours, so the final figure appears the next day.

## What Cost Explorer showed

The day after, Cost Explorer for **5–6 October 2026** ([`34`](screenshots/34-cost-explorer-oct-5-6.png)), grouped by service. The range is inclusive, so it covers the three builds I ran on 5 October (`aws-aurora-ha-architecture`, `aws-shared-file-storage` and `aws-hybrid-storage-transfer`), whatever had posted of 6 October (when I ran `aws-route53-routing-lab`), and the services that run in the account all the time:

| Service | Cost |
|---|---|
| Config (always on, from `aws-cloudtrail-config-governance`) | US$1.37 |
| EC2-Instances (all three builds) | US$0.90 |
| Relational Database Service (the Aurora build) | US$0.39 |
| FSx | US$0.18 |
| EC2-Other (EBS volumes, including the gateway's cache disk) | US$0.17 |
| Security Hub (always on) | US$0.12 |
| DataSync | US$0.10 |
| Elastic File System | US$0.09 |
| VPC | US$0.06 |
| Others | US$0.15 |
| **Total** | **US$3.53** |

This build's own lines are DataSync (US$0.10, close to the US$0.11 I estimated for ~8.5 GB) plus its share of EC2 and EC2-Other: the agent, the gateway and its 150 GiB cache disk. Leaving out Config and Security Hub, which run whatever I build, everything else came to about **US$2.04**: mainly the three 5 October builds, plus whatever of 6 October had posted. That's well under my estimates for the three builds added together. Cost Explorer can still be catching up on the most recent day, so I treat this as a floor rather than a final bill.

## What the real migration costs

| Item | Kgotla's scale | Approx. cost |
|---|---|---|
| DataSync copying | 40 TB once (40,000 GB × US$0.0125) | **~US$500** |
| Catch-up runs (`TransferMode=CHANGED`) | only what changed since the last run | small |
| Agent on-premises | a VM on Kgotla's own hypervisor | no AWS charge |
| S3 Standard | 40 TB × ~US$0.023/GB-month | ~US$920/month |
| S3 Glacier Flexible Retrieval for archives older than a year | ~US$0.0036/GB-month | ~US$144/month per 40 TB |

The archive is rarely read, so the storage line is the one to optimise: a lifecycle rule moving old scans to a Glacier tier cuts the monthly bill by most of its value. That's the follow-on in `aws-backup-archival-tested-restore`.

## Running costs after the migration

| Service | Ongoing cost driver |
|---|---|
| S3 File Gateway | On-premises VM: no hourly AWS fee. S3 storage and requests for `gateway/` |
| Transfer Family | ~US$216/month per protocol endpoint (US$0.30 × 720 hours), plus US$0.04/GB. This replaces a server, its patching and its licence |
| CloudWatch Logs | Per GB ingested and stored; set a retention period on the SFTP log group |

## Cost traps

- **Leaving the agent or gateway instance running** after a lab is the expensive mistake: about US$22 a day for everything in this build together.
- **Deleting the agent or gateway in AWS doesn't stop the EC2 instance.** `terminate-instances` does, and takes the 150 GiB cache disk with it (`DeleteOnTermination=true`).
- **The SFTP endpoint bills while it exists, even with no sessions.** For occasional deliveries, stopping the server doesn't stop the hourly charge; only deleting it does.
