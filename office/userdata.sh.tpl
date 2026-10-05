#!/bin/bash
# Boot script for kgotla-office: an office PC with the NFS client and the officetool command.
set -euxo pipefail
dnf install -y nfs-utils
mkdir -p /opt/office
cat > /opt/office/config.json <<'CFG'
{"region": "@@REGION@@"}
CFG
base64 -d <<'OFFICETOOL' | gunzip > /opt/office/officetool.py
@@OFFICETOOL_GZ_B64@@
OFFICETOOL
printf '#!/bin/bash\nexec sudo python3 /opt/office/officetool.py "$@"\n' > /usr/local/bin/officetool
chmod 755 /usr/local/bin/officetool /opt/office/officetool.py
echo "officetool ready"
