# NAS SNMP Monitor API

Real-time Synology NAS monitoring via SNMPv3, exposed as a FastAPI service with 1-minute averaged metrics and remote event logging for Benchmarking.

## Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)
- SNMPv3 user on NAS with **authNoPriv** (SHA, no encryption)

## Setup

```bash
uv sync
```

Configure the NAS IPs and credentials in `api.py`:
```python
NAS_DEVICES = {
    "smlnas": {"host": "192.168.250.139", "name": "SmlNAS-10G"},
    # "bignas": {"host": "192.168.250.182", "name": "BigNAS-10G"},
}
SNMP_USER = "wangup"
SNMP_AUTH = "yourpassword"
```

## Running

```bash
# Start in background (default 2s interval)
./start.sh

# High-resolution mode for benchmarking (1s interval)
./start.sh 1

# Stop
./stop.sh

# View logs
tail -f api.log
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /metrics/{device}` | Latest real-time metrics |
| `GET /metrics/{device}/avg/1m` | 1-minute windowed average |
| `POST /metrics/{device}/event` | Insert a named marker into the log |
| `GET /summary` | Quick overview of all devices |
| `GET /health` | Collector health + sample count |

## Benchmarking Integration

Copy `nas_monitor_client.py` to your benchmark project and use:

```python
from nas_monitor_client import NASMonitorClient
client = NASMonitorClient(host="snmp-monitor", device="smlnas")

client.mark_event("START_MY_BENCHMARK")
# ... run your I/O task ...
client.mark_event("END_MY_BENCHMARK")
```

Then generate a plot with start/end markers:
```bash
uv run python examples/plot_results.py
```

## File Structure

| File | Role |
|---|---|
| `api.py` | FastAPI server entry point |
| `collector.py` | Low-level SNMP fetching |
| `manager.py` | Background polling, averaging, JSONL logging |
| `model.py` | Pydantic schemas |
| `nas_monitor_client.py` | **Portable client** — copy to your benchmark project |
| `examples/zarr_demo.py` | Example: Zarr write + monitoring |
| `examples/plot_results.py` | Reads JSONL log and generates benchmark plot |
| `compose.yml` | Podman/Docker service definition |

## Metrics Collected

| Category | Fields |
|---|---|
| **Storage IO** | Per-disk Read/Write MB/s, R/W IOPS, Load % (1-min avg) |
| **Network** | Per-interface RX/TX MB/s |
| **System** | Temp, fans, power, CPU%, RAM% |
| **Volumes / RAID / Disks** | Usage %, health, status |

## Notes

- `load_pct` uses 1-minute average (col `.8`) — Synology does not expose instant load via SNMP
- Raw metrics are logged to `nas_metrics_history_raw.jsonl` automatically
- `storageIO` device names (`sata1`…) are kernel names, not Synology slot labels
