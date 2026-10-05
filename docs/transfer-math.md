# How long will 40 TB take?

The board's question was "how long, and do we need to ship disks?". The answer is arithmetic, and I fed it a rate I measured rather than a vendor figure.

## The calculation

[`scripts/transfer_calc.py`](../scripts/transfer_calc.py) uses decimal units, the way links and disks are sold: 1 TB = 10^12 bytes, 1 Mbps = 10^6 bits per second.

40 TB = 320 terabits. At 100 Mbps that is 3,200,000 seconds, or **37.0 days** with nothing else on the line.

I ran it with 80% of each link available for the migration and the measured full-speed rate taken straight from the results CSV ([`16`](screenshots/16-step7-transfer-calculator-and-csv.png)):

```
Moving 40 TB (320 Tbit)

                  link       usable   time at 100%    time at 80%
         100 Mbps line      80 Mbps      37.0 days      46.3 days
        1000 Mbps line     800 Mbps       3.7 days       4.6 days
    measured 1260 Mbps    1008 Mbps       2.9 days       3.7 days
```

## What I told the board

| Option | Time for 40 TB | Fits? |
|---|---|---|
| Today's 100 Mbps line, all of it, around the clock | 37 days | No: the business needs the line |
| Today's line at the 50 Mbps working-day limit I tested | about 74 days at 50 Mbps all day; somewhat less if nights run faster | No |
| A 1 Gbps link for the migration, 80% used | **4.6 days** | Yes |
| One DataSync agent, unlimited (my measured 1,260 Mbps) at 80% | 3.7 days | The agent isn't the bottleneck; the link is |
| Offline transfer | days of shipping/handling plus the copy at each end | Worth pricing when the link can't be upgraded |

**Recommendation:** a temporary 1 Gbps link (or Direct Connect) for the bulk copy, DataSync with a working-hours limit on the existing line until it arrives, and a final `CHANGED` run to catch up before the cut-over. Price offline transfer as the fallback.

On offline transfer: AWS Snowball Edge is no longer available to new customers. AWS now points to **AWS Data Transfer Terminals** (you bring your own storage to an AWS-run facility and upload over a high-speed connection) and partner services.

## The rule of thumb I use

If the online transfer takes longer than about a week at the share of the link the business can spare, price an offline option or a faster link as well. At 40 TB on 100 Mbps, it's more than six weeks.
