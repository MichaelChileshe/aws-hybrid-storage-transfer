#!/usr/bin/env python3
"""Regenerates docs/architecture.svg + docs/architecture.png using the OFFICIAL AWS Architecture Icons.

The icon pack is not committed (AWS licenses it for diagrams, not redistribution). Download it from
https://aws.amazon.com/architecture/icons/, unzip, then:

    AWS_ICONS_DIR=/path/to/unzipped-icon-package python3 build_architecture.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from awsdiag import Diagram, GREY, INK

ACT, SG = "#5A6B86", "#D13212"
MIG, GW, SFTP = "#7AA116", "#0073BB", "#C925D1"
d = Diagram(1900, 1130)

d.text(40, 40, "Leaving the server room: DataSync migration, S3 File Gateway and Transfer Family SFTP", 19, "bold")
d.text(40, 64, "Kgotla Financial Services  ·  the server room simulated in a VPC, the appliances from AWS's own images  ·  "
               "outbound HTTPS only  ·  us-east-1", 13, "normal", GREY)

d.group("cloud", 20, 90, 1500, 1020, "AWS Cloud")
d.group("region", 40, 130, 1460, 960, "us-east-1")
d.group("vpc", 60, 175, 770, 890, "kgotla-dc-vpc  10.80.0.0/16  (stands in for Kgotla's server room)")
d.group("public", 80, 215, 730, 790, "kgotla-dc-a  10.80.1.0/24  ·  us-east-1a")


def node(key, x, y, title, lines=(), color=INK, size=48):
    d.icon(key, x, y, size)
    d.text(x + size + 10, y + 16, title, 12.5, "bold", color)
    for i, l in enumerate(lines):
        d.text(x + size + 10, y + 33 + i * 16, l, 11, "normal", GREY)


# ------------------------------------------------------------------ the server room
d.text(102, 262, "THE ARCHIVE (40 TB in real life)", 11, "bold", MIG)
node("ec2_instance", 105, 274, "kgotla-nas  10.80.1.174", ["t3.small · NFS export /srv/archive (ro)",
     "4 x 768 MiB scans", "2,000 x 512 KiB ledgers"], MIG)
d.text(553, 262, "AWS APPLIANCE", 11, "bold", MIG)
node("datasync_agent", 495, 274, "kgotla-datasync-agent", ["10.80.1.170 · m5.2xlarge",
     "DataSync AMI", "no role, no key pair"], MIG)
d.line([(378, 298), (490, 298)], MIG, width=2.4)
d.label(384, 330, "NFS, read-only", MIG, 10.5)

d.text(102, 712, "THE OFFICE", 11, "bold", GW)
node("ec2_instance", 105, 724, "kgotla-office", ["t3.micro · Session Manager only",
     "officetool: mount, write, ls"], GW)
d.text(553, 712, "AWS APPLIANCE", 11, "bold", GW)
node("s3_file_gateway", 495, 724, "kgotla-file-gateway", ["10.80.1.228 · m5.xlarge",
     "S3 File Gateway AMI (FILE_S3)"], GW)
d.line([(370, 748), (490, 748)], GW, width=2.4)
d.label(376, 780, "NFS /kgotla-archive", GW, 10.5)

d.box(495, 812, 300, 92, GW, fill="#F0F6FC", dashed=False)
d.text(507, 832, "NFS share /kgotla-archive -> gateway/", 11.5, "bold", GW)
d.text(507, 850, "150 GiB gp3 cache disk (/dev/nvme1n1)", 11, "normal", INK)
d.text(507, 867, "clients 10.80.1.0/24 only · RootSquash", 11, "normal", INK)
d.text(507, 884, "cache refresh: on demand + every 300 s", 11, "normal", INK)

# activation path (port 80, office -> appliance, once)
d.line([(129, 722), (129, 640), (519, 640), (519, 380)], ACT, dashed=True, width=1.8)
d.line([(519, 640), (519, 720)], ACT, dashed=True, width=1.8)
d.label(150, 632, "port 80, used once: activation key fetched from the office PC", ACT, 10.5)

# security groups
d.box(105, 420, 360, 170, SG, fill="#FFFFFF", dashed=True)
d.text(117, 442, "Security groups: SG-to-SG, one way only", 12, "bold", SG)
for i, (g, t) in enumerate([("office-sg", "no inbound at all"), ("agent-sg", "80 from office-sg"),
                             ("nas-sg", "2049 / 111 / 20048 from agent-sg"),
                             ("gateway-sg", "80 / 2049 / 111 / 20048 from office-sg")]):
    d.text(117, 466 + i * 20, g, 11, "bold", INK)
    d.text(207, 466 + i * 20, t, 11, "normal", INK)
d.text(117, 554, "8 rules · no group refers back to its source,", 11, "normal", GREY)
d.text(117, 572, "so teardown deletes them in plain order", 11, "normal", GREY)

d.icon("igw", 806, 940, 44)
d.text(798, 958, "internet gateway: outbound", 10.5, "normal", GREY, "end")
d.text(798, 972, "HTTPS to AWS endpoints", 10.5, "normal", GREY, "end")

# ------------------------------------------------------------------ AWS services
node("datasync", 900, 274, "AWS DataSync", ["task kgotla-archive-migration",
     "verify: POINT_IN_TIME_CONSISTENT", "bandwidth limit per run (BytesPerSecond)"], MIG)
d.line([(722, 298), (895, 298)], MIG, width=2.4)
d.label(735, 290, "HTTPS 443 out", MIG, 10.5)

node("transfer_family", 1180, 274, "AWS Transfer Family", ["SFTP · public endpoint",
     "service-managed users, SSH keys", "LOGICAL home + session policy"], SFTP)

d.box(880, 440, 600, 200, "#3F8624", fill="#F7FAF3", dashed=False)
d.icon("s3_bucket", 894, 452, 44)
d.text(948, 472, "S3  kgotla-hybrid-&lt;account&gt;", 13, "bold", "#3F8624")
d.text(948, 489, "private: all four public-access blocks on · encrypted at rest (SSE-S3)", 11, "normal", GREY)
d.text(900, 522, "migration/", 12, "bold", MIG)
d.text(1040, 522, "2,007 objects, 4,269,801,472 bytes, verified", 11.5)
d.text(900, 556, "gateway/", 12, "bold", GW)
d.text(1040, 556, "scan-130730.pdf (from the office) · direct-to-s3.txt", 11.5)
d.text(900, 590, "partners/", 12, "bold", SFTP)
d.text(1040, 590, "partner-acme/acme-invoice-0001.csv", 11.5)
d.text(1040, 607, "partner-umoya/umoya-statement-0001.csv", 11.5)
d.text(900, 630, "each service's role can write only its own prefix", 10.5, "normal", GREY)

d.line([(924, 340), (924, 438)], MIG, width=2.2)
d.line([(1204, 340), (1204, 438)], SFTP, width=2.2)
d.line([(800, 748), (850, 748), (850, 552), (878, 552)], GW, width=2.2)
d.label(856, 652, "HTTPS 443 out", GW, 10.5)

node("storage_gateway", 900, 680, "AWS Storage Gateway", ["kgotla-file-gateway, FILE_S3, GMT+2:00",
     "RefreshCache on demand"], GW, 44)
node("iam_role", 900, 770, "Four service roles", ["DataSync, gateway, SFTP users, SFTP logging",
     "aws:SourceAccount on every trust policy"], INK, 40)
node("ssm", 900, 860, "Systems Manager", ["Session Manager shell on the office PC",
     "Run Command fetches activation keys"], INK, 44)
node("cw_logs", 900, 950, "CloudWatch Logs", ["/aws/transfer/&lt;server-id&gt;",
     "one stream per partner session"], SFTP, 44)

node("tape_gateway", 1200, 860, "Tape Gateway (not built)", ["the path if a backup product", "must keep writing to tape"],
     GREY, 40)

# ------------------------------------------------------------------ partners (outside AWS)
d.icon("users", 1560, 120, 48)
d.text(1618, 138, "Partners: Acme, Umoya", 12.5, "bold", SFTP)
d.text(1618, 154, "SFTP with their own ed25519 key", 11, "normal", GREY)
d.line([(1584, 172), (1584, 230), (1204, 230), (1204, 270)], SFTP, width=2.2)
d.label(1300, 222, "SFTP port 22: each lands in its own folder", SFTP, 10.5)

# ------------------------------------------------------------------ results + legend
bx, by = 1540, 260
d.box(bx, by, 345, 470, "#D5DBDB", fill="#fff", dashed=False)
d.text(bx + 14, by + 26, "Measured", 13.5, "bold")
rows = [
    ("DataSync, no limit", MIG, ["2,007 files, 4.27 GB, verified", "transfer 27 s: 157.5 MB/s = 1,260 Mbps"]),
    ("DataSync, 50 Mbps limit", MIG, ["same 4.27 GB in 695 s, verified", "average 6.1 MB/s = 49 Mbps"]),
    ("40 TB at 80% of the line", INK, ["100 Mbps: 46.3 days", "1 Gbps: 4.6 days", "one agent at 1,260 Mbps: 3.7 days"]),
    ("File Gateway write-back", GW, ["saved 13:07:30 UTC, in S3 13:07:31", "owner nobody (root squashed)"]),
    ("Cache trap", GW, ["object put straight into S3: listed", "on the share after RefreshCache"]),
    ("SFTP isolation", SFTP, ["Acme: 'cd ..' still at /", "Umoya fetching Acme's file: not found x2"]),
]
y = by + 54
for title, c, ls in rows:
    d.text(bx + 14, y, title, 12, "bold", c)
    for l in ls:
        y += 18
        d.text(bx + 14, y, l, 11.5)
    y += 28

lx, ly = 1540, 760
d.raw(f'<rect x="{lx}" y="{ly}" width="345" height="150" rx="4" fill="#fff" stroke="#D5DBDB"/>')
d.text(lx + 12, ly + 22, "Legend", 13, "bold")
leg = [(MIG, False, "archive migration (DataSync)"), (GW, False, "office share (S3 File Gateway)"),
       (SFTP, False, "partner deliveries (Transfer Family)"), (ACT, True, "one-time appliance activation")]
for i, (c, dash, t) in enumerate(leg):
    yy = ly + 46 + i * 26
    d.line([(lx + 12, yy), (lx + 58, yy)], c, dashed=dash)
    d.text(lx + 66, yy + 4, t, 11.5)

here = os.path.dirname(os.path.abspath(__file__))
d.save(os.path.join(here, "..", "architecture.svg"), os.path.join(here, "..", "architecture.png"))
print("wrote docs/architecture.svg and docs/architecture.png")
