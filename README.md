# nas-sys-monitoring

Real-time Synology NAS monitoring via SNMPv3, polling every second and printing to stdout.

## Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)
- SNMPv3 user configured on the NAS with **authNoPriv** (SHA auth, no encryption)

## Setup

```bash
uv sync
```

Edit the credentials at the top of `main.py`:

```python
NAS_HOST   = "192.168.250.182"
SNMP_USER  = "wangup"
SNMP_AUTH  = "yourpassword"
AUTH_PROTO = "SHA"   # or MD5
```

## Run

```bash
uv run python -u main.py
```

The `-u` flag disables output buffering so values print immediately.

## What it monitors

| Section | Details |
|---|---|
| **System** | Model, temperature, power, fan status (requires SNMP access to Synology System MIB) |
| **CPU** | Overall utilization %, per-core load |
| **RAM** | Utilization % |
| **Volumes** | Per-mount used/total/% |
| **RAID** | Name, status, used/total/% |
| **Disks** | Model, type, status, health, role, temperature, retries, bad sectors, remaining life (SSD) |
| **StorageIO** | Per-disk read/write MB/s and IOPS, load % — computed as delta of cumulative SNMP counters across each 1-second interval |
| **Network** | Per-interface status, speed, live RX/TX MB/s |

## Notes

- **System MIB** (model, temp, fans, CPU%, RAM%) requires the SNMP user to have read access to OID `1.3.6.1.4.1.6574.1` in DSM → Control Panel → Terminal & SNMP → SNMPv3.
- StorageIO device names (`sata1`, `sata2`, …) are kernel names and do not directly map to Synology's disk slot names (`Disk 6`, `Disk 7`, …).
- `remain_life = -1%` on HDDs is expected — that field is only meaningful for SSDs.
