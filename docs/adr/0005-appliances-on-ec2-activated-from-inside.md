# ADR 0005: Simulate the server room in a VPC; activate the appliances from inside it

**Status:** Accepted
**Context:** The DataSync agent and File Gateway run as VMs in Kgotla's server room. I needed to build and test them the way they'd really run, without a physical site.

## Options considered

| Option | Verdict |
|---|---|
| Run the appliances on a home hypervisor | ❌ Not reproducible by anyone reading this repo; home internet would skew the measurements |
| Open port 80 on the appliances to the internet and activate from my laptop | ❌ Works, but exposes the appliances; not how a real server room would do it |
| **A VPC as the "server room", appliances from AWS's own AMIs, activation from the office PC over SSM** | ✅ Chosen |

## Decision

- **Network:** `kgotla-dc-vpc` holds the NAS, an office PC and both appliances in one subnet. The appliances reach AWS over outbound HTTPS through an internet gateway, like a server room's internet line.
- **Images:** they come from the public SSM parameters `/aws/service/datasync/ami` and `/aws/service/storagegateway/ami/FILE_S3/latest`, with no instance role and no key pair.
- **Activation:** [`scripts/activation_key.py`](../../scripts/activation_key.py) runs `curl` on the office PC through SSM Run Command against the appliance's private IP and returns only the key.
- **Ports:** port 80 is open only from the office PC's security group; in production the rule would be removed once both appliances are activated.

## Consequences

- Both keys came back in 7 seconds, and nothing in the "server room" accepts a connection from outside it.
- In production, the same script pattern works from any admin machine on Kgotla's network. The appliances would run on Kgotla's hypervisor and reach AWS over the VPN or Direct Connect, with DataSync on a VPC (PrivateLink) endpoint.
- EC2 bandwidth inside a region is far higher than a real office line, which is why the measured rate feeds the calculator as "what the agent can do", not "what Kgotla's line can do".
