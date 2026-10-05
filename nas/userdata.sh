#!/bin/bash
# Boot script for kgotla-nas: the "on-premises" file server holding the archive DataSync will migrate.
set -euxo pipefail
dnf install -y nfs-utils
mkdir -p /srv/archive/scans /srv/archive/ledgers
# 4 large scanned-document archives (768 MiB each) - random data, so nothing compresses in transit
for i in 1 2 3 4; do dd if=/dev/urandom of=/srv/archive/scans/archive-$i.bin bs=1M count=768 status=none; done
# 2,000 small ledger exports (512 KiB each)
for i in $(seq -w 1 2000); do head -c 524288 /dev/urandom > /srv/archive/ledgers/ledger-$i.dat; done
chmod -R a+rX /srv/archive
echo "/srv/archive 10.80.0.0/16(ro)" > /etc/exports
systemctl enable --now nfs-server
exportfs -rav
du -sh /srv/archive; find /srv/archive -type f | wc -l
echo "nas ready"
