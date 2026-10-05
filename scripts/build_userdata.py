#!/usr/bin/env python3
"""Build the office PC's boot script with the officetool tool embedded (gzip + base64).

Usage:  python3 scripts/build_userdata.py            -> writes build/office-userdata.sh
"""
import base64, gzip, os, textwrap
from kit_aws import ROOT, env

tpl = open(os.path.join(ROOT, "office", "userdata.sh.tpl")).read()
tool = open(os.path.join(ROOT, "office", "officetool.py"), "rb").read()
packed = "\n".join(textwrap.wrap(base64.b64encode(gzip.compress(tool, 9)).decode(), 76))
text = tpl.replace("@@REGION@@", env("REGION")).replace("@@OFFICETOOL_GZ_B64@@", packed)
os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
dst = os.path.join(ROOT, "build", "office-userdata.sh")
with open(dst, "w", newline="\n") as f:
    f.write(text)
size = os.path.getsize(dst)
print(f"built {dst}  ({size:,} bytes; EC2 limit is 16,384)")
if size > 16384:
    raise SystemExit("too big for EC2 user data")
