#!/usr/bin/env python3
"""Watch an S3 prefix and report the first NEW object that appears, with its upload time and metadata.

  python3 scripts/wait_s3.py <prefix>        e.g.  gateway/

Start it, then write a file through the gateway. Prints how long after starting the object appeared, the
object's LastModified (when S3 received it) and the POSIX metadata the gateway attached.
"""
import json, sys, time
from kit_aws import aws, env


def keys(bucket, prefix):
    res = aws("s3api", "list-objects-v2", "--bucket", bucket, "--prefix", prefix)
    return {o["Key"] for o in res.get("Contents", [])}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    bucket, prefix = env("BUCKET"), sys.argv[1]
    before = keys(bucket, prefix)
    t0 = time.time()
    print(f"watching s3://{bucket}/{prefix} ({len(before)} objects already there) - write the file now", flush=True)
    while time.time() - t0 < 600:
        time.sleep(1)
        new = keys(bucket, prefix) - before
        if new:
            k = sorted(new)[0]
            h = aws("s3api", "head-object", "--bucket", bucket, "--key", k)
            print(f"\nappeared after {time.time() - t0:.0f} s of watching: s3://{bucket}/{k}")
            print(f"  LastModified (S3 received it): {h['LastModified']}")
            print(f"  size: {h['ContentLength']:,} bytes")
            print(f"  metadata set by the gateway: {json.dumps(h.get('Metadata', {}))}")
            return
    sys.exit("nothing new after 10 minutes")


if __name__ == "__main__":
    main()
