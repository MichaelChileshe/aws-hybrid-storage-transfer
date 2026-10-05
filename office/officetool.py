#!/usr/bin/env python3
"""officetool - Kgotla's office PC, talking to the File Gateway's NFS share. Runs as root (via sudo).

  officetool mount           find the gateway's file share and mount it at /mnt/archive
  officetool write           write one 5 MiB "scanned document" and print the exact time it was written
  officetool ls              list the share

The gateway and its share are discovered through the AWS CLI and the instance role (read-only), so no IP
addresses are typed. Python 3.9 compatible (Amazon Linux 2023).
"""
import json, os, subprocess, sys, time
from datetime import datetime, timezone

REGION = json.load(open("/opt/office/config.json"))["region"]
MOUNT = "/mnt/archive"


def out(msg=""):
    print(msg, flush=True)


def die(msg):
    sys.exit(f"\nERROR: {msg}\n")


def aws(*args):
    r = subprocess.run(["aws", *args, "--region", REGION, "--output", "json"], capture_output=True, text=True)
    if r.returncode != 0:
        die(f"aws {' '.join(args[:2])} failed:\n{r.stderr.strip()}")
    return json.loads(r.stdout) if r.stdout.strip() else {}


def share():
    shares = aws("storagegateway", "list-file-shares")["FileShareInfoList"]
    nfs = [s for s in shares if s.get("FileShareType") == "NFS"]
    if not nfs:
        die("no NFS file share found on any gateway yet")
    info = aws("storagegateway", "describe-nfs-file-shares",
               "--file-share-arn-list", nfs[0]["FileShareARN"])["NFSFileShareInfoList"][0]
    gw = aws("storagegateway", "describe-gateway-information", "--gateway-arn", info["GatewayARN"])
    ip = gw["GatewayNetworkInterfaces"][0]["Ipv4Address"]
    return ip, info["Path"], info["FileShareStatus"]


def mount(_):
    if subprocess.run(["mountpoint", "-q", MOUNT]).returncode == 0:
        out(f"{MOUNT} is already mounted")
        return
    ip, path, status = share()
    out(f"gateway {ip}, share {path} ({status})")
    os.makedirs(MOUNT, exist_ok=True)
    cmd = f"mount -t nfs -o nolock,hard {ip}:{path} {MOUNT}"
    out(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        die((r.stdout + r.stderr).strip())
    out(f"mounted at {MOUNT}")


def write(_):
    stamp = datetime.now(timezone.utc).strftime("%H%M%S")
    name = f"scan-{stamp}.pdf"
    path = os.path.join(MOUNT, name)
    with open(path, "wb") as fh:
        fh.write(os.urandom(5 * 1024 * 1024))
        fh.flush()
        os.fsync(fh.fileno())
    out(f"wrote {name} (5 MiB) at {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC")


def ls(_):
    subprocess.run(["ls", "-l", MOUNT])


def main():
    if os.geteuid() != 0:
        die("run as root (the officetool wrapper uses sudo)")
    cmds = {"mount": mount, "write": write, "ls": ls}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        out(__doc__)
        return
    cmds[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
