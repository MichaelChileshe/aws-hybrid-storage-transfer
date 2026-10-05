#!/usr/bin/env python3
"""Get an activation key from a DataSync agent or a Storage Gateway appliance, asked from INSIDE the network.

The appliance only answers on port 80 to machines that can reach it, exactly like in a real data centre. This
script uses SSM Run Command to run curl on the office PC, retrying while the appliance is still booting, and
prints ONLY the key on stdout (progress goes to stderr), so it can be wrapped in  save NAME "$(...)".

  python3 scripts/activation_key.py <office-instance-id> <appliance-private-ip> sync      (DataSync agent)
  python3 scripts/activation_key.py <office-instance-id> <appliance-private-ip> gateway   (Storage Gateway)
"""
import json, re, subprocess, sys, time

KEY = re.compile(r"[A-Z0-9]{5}(?:-[A-Z0-9]{5}){4}")


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def aws(*args):
    r = subprocess.run(["aws", *args, "--output", "json"], capture_output=True, text=True)
    return (json.loads(r.stdout) if r.stdout.strip() else {}) if r.returncode == 0 else None


def run_on(iid, command):
    sent = aws("ssm", "send-command", "--instance-ids", iid, "--document-name", "AWS-RunShellScript",
               "--parameters", json.dumps({"commands": [command]}), "--comment", "get activation key")
    if not sent:
        return None
    cid = sent["Command"]["CommandId"]
    for _ in range(30):
        time.sleep(3)
        inv = aws("ssm", "get-command-invocation", "--command-id", cid, "--instance-id", iid)
        if inv and inv["Status"] not in ("Pending", "InProgress", "Delayed"):
            return inv.get("StandardOutputContent", "").strip()
    return None


def main():
    if len(sys.argv) != 4 or sys.argv[3] not in ("sync", "gateway"):
        sys.exit(__doc__)
    office, ip, kind = sys.argv[1:]
    url = (f"http://{ip}/?gatewayType=SYNC&activationRegion=us-east-1&no_redirect" if kind == "sync"
           else f"http://{ip}/?activationRegion=us-east-1&no_redirect")
    log(f"asking {ip} for a {kind} activation key from the office PC (retrying while it boots, up to 15 min)")
    t0 = time.time()
    while time.time() - t0 < 900:
        answer = run_on(office, f'curl -s -m 10 "{url}"')
        found = KEY.search(answer or "")
        if found:
            log(f"got the key after {int(time.time() - t0)} s (valid for 30 minutes)")
            print(found.group(0))
            return
        log(f"  not ready yet ({int(time.time() - t0)} s): {(answer or 'no answer')[:60]}")
        time.sleep(20)
    sys.exit("no activation key after 15 minutes - check the instance is running and the SG allows port 80 "
             "from the office PC")


if __name__ == "__main__":
    main()
