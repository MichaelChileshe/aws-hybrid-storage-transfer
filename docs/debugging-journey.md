# Debugging journey

Fewer things broke in this build than in the last two, mostly because I designed around the problems I'd already met. The ones that did come up are still worth knowing.

---

## 1 · Raising the bandwidth limit mid-run had no visible effect

`aws datasync update-task-execution --options BytesPerSecond=25000000` returned no output and no error ([`14`](screenshots/14-step6-update-task-execution.png)), but the interval rates stayed in the same 62–66 Mbps band (with 0.0 gaps) as before the update, and the run averaged 49 Mbps ([`15`](screenshots/15-step6-throttled-run-result.png)).

I didn't check `aws datasync describe-task-execution --query Options.BytesPerSecond` straight after the update, which would have told me whether the new value had been stored. That's the next test.

**Lesson:** "no error" isn't "it worked". After any change to a running job, read the setting back and watch a metric that should move. Until this is proven, the safe plan is separate scheduled runs with different limits.

---

## 2 · Interval rates above the limit, and intervals of zero

In the 50 Mbps run, most 10-second intervals read about 62–66 Mbps, and every few intervals read 0.0. On its own that looks like the limit being exceeded.

The average over the 695-second transfer was 49 Mbps. DataSync's `BytesTransferred` counter updates in steps, so a short window can catch two updates or none.

**Lesson:** judge a throttle on the average over a long window, not on one sample.

---

## 3 · LAUNCHING took about 90 seconds

Both runs sat in `LAUNCHING` with 0.00 GB moved for about a minute and a half (the first started 14:23:51; its first `TRANSFERRING` poll was 14:25:30) before transferring ([`11`](screenshots/11-step5-full-speed-run-live.png), [`13`](screenshots/13-step6-throttled-run-50-mbps.png)). That's DataSync starting the run, not a stuck agent.

**Lesson:** for planning, use the transfer-phase rate. A fixed minute or two at the start is irrelevant over 40 TB, and including it would understate the rate of a small test.

---

## 4 · The calculator needed the measured rate, not a retyped one

The calculator takes `--measured-mbps`. Rather than reading 1,260 off the screen and typing it, I pulled it from the results CSV with `awk`:

```bash
python3 scripts/transfer_calc.py --tb 40 --links 100,1000 --util 0.8 \
  --measured-mbps "$(awk -F, '$1=="full-speed"{print $NF}' build/datasync-results.csv)"
```

**Lesson:** when one script's output feeds another, pass it by command substitution. The table and the CSV can't disagree.

---

## 5 · Designed out: NFSv3 needs more than port 2049

NFSv3 mounts use the portmapper (111) and `mountd` (20048) as well as 2049. The NAS group allows all three from the agent, and the gateway group allows all three (plus 80 for activation) from the office PC. Missing 20048 is a classic cause of a mount that hangs with no clear error.

---

## 6 · Designed out: security groups that block each other's deletion

In the shared-storage build, two groups referenced each other and `delete-security-group` failed with `DependencyViolation` until I revoked both groups' rules. This time every rule points one way: office → agent and gateway, agent → NAS. The teardown deletes the groups in plain order: NAS, gateway, agent, office.

---

## 7 · Designed out: activation keys from outside the network

An appliance only gives its activation key to something that can reach it on port 80. Opening port 80 to the internet would work and would be wrong. [`scripts/activation_key.py`](../scripts/activation_key.py) runs `curl` on the office PC through SSM Run Command, using `no_redirect` so the appliance returns the key instead of redirecting a browser. The only port-80 rules are from the office PC's group, and both keys came back in 7 seconds ([`09`](screenshots/09-step4-agent-activated-online.png), [`17`](screenshots/17-step8-gateway-activated-cache-added.png)).

---

## 8 · Small things that held

- `sudo cloud-init status --wait` on the office PC: as `ssm-user`, the plain command fails on a root-only file.
- The office terminal opened with one chained line, so it always has the saved values: `cd ~/hybrid-transfer && source ./env.sh && aws ssm start-session --target "$OFFICE_ID"`.
- Every JMESPath query with backticks or `!` in single quotes, so the shell leaves it alone.
- A share on an S3 prefix: trailing slash on the location ARN, plus `--file-share-name`.
