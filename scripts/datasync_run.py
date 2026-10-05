#!/usr/bin/env python3
"""Run the DataSync task once, watch it, and report the transfer rate.

  python3 scripts/datasync_run.py <label> [--all] [--mbps N]

  --all       transfer everything again (TransferMode=ALL), not just what changed
  --mbps N    bandwidth limit in megabits per second (sets BytesPerSecond = N x 125,000)

Every 10 s it prints the phase, bytes moved so far and the rate over that interval (so a mid-run change of the
limit with update-task-execution shows up immediately). The running execution's ARN is written to
build/current-execution.txt. The final result is appended to build/datasync-results.csv.
"""
import csv, json, os, subprocess, sys, time
from kit_aws import ROOT, aws, env


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    label = sys.argv[1]
    args = sys.argv[2:]
    opts = []
    limit = None
    if "--all" in args:
        opts.append("TransferMode=ALL")
    if "--mbps" in args:
        limit = float(args[args.index("--mbps") + 1])
        opts.append(f"BytesPerSecond={int(limit * 125000)}")
    cmd = ["datasync", "start-task-execution", "--task-arn", env("TASK_ARN")]
    if opts:
        cmd += ["--override-options", ",".join(opts)]
    exe = aws(*cmd)["TaskExecutionArn"]
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    open(os.path.join(ROOT, "build", "current-execution.txt"), "w").write(exe + "\n")
    print(f"{time.strftime('%H:%M:%S')}  started '{label}'  limit: {f'{limit:g} Mbps' if limit else 'none'}")
    print(f"  execution: {exe}", flush=True)
    last_b, last_t = 0, time.time()
    while True:
        time.sleep(int(os.environ.get("DS_POLL","10")))
        d = aws("datasync", "describe-task-execution", "--task-execution-arn", exe)
        st, b, now = d["Status"], d.get("BytesTransferred", 0), time.time()
        rate = (b - last_b) / (now - last_t) / 1e6
        print(f"  {time.strftime('%H:%M:%S')}  {st:<13} {b / 1e9:7.2f} GB moved   last 10 s: {rate:7.1f} MB/s "
              f"= {rate * 8:7.1f} Mbps", flush=True)
        last_b, last_t = b, now
        if st in ("SUCCESS", "ERROR"):
            break
    r = d.get("Result", {})
    if st == "ERROR":
        sys.exit(f"\nERROR: {r.get('ErrorCode', '')} {r.get('ErrorDetail', '')}")
    secs = r.get("TransferDuration", 0) / 1000 or 1
    mbs = d.get("BytesTransferred", 0) / secs / 1e6
    print("\nRESULT", label)
    print(f"  files transferred : {d.get('FilesTransferred', 0):,}")
    print(f"  bytes transferred : {d.get('BytesTransferred', 0) / 1e9:.2f} GB")
    print(f"  phases (s)        : prepare {r.get('PrepareDuration', 0) / 1000:.0f}  transfer {secs:.0f}  "
          f"verify {r.get('VerifyDuration', 0) / 1000:.0f}  total {r.get('TotalDuration', 0) / 1000:.0f}")
    print(f"  transfer rate     : {mbs:.1f} MB/s = {mbs * 8:.0f} Mbps (bytes / transfer phase)")
    print(f"  verification      : {r.get('VerifyStatus', 'n/a')}")
    path = os.path.join(ROOT, "build", "datasync-results.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["label", "limit_mbps", "files", "gb", "prepare_s", "transfer_s", "verify_s", "total_s", "MBps", "Mbps"])
        w.writerow([label, limit or "", d.get("FilesTransferred", 0), f"{d.get('BytesTransferred', 0) / 1e9:.2f}",
                    f"{r.get('PrepareDuration', 0) / 1000:.0f}", f"{secs:.0f}", f"{r.get('VerifyDuration', 0) / 1000:.0f}",
                    f"{r.get('TotalDuration', 0) / 1000:.0f}", f"{mbs:.1f}", f"{mbs * 8:.0f}"])
    print(f"  saved to build/datasync-results.csv")


if __name__ == "__main__":
    main()
