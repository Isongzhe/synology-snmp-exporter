from fastapi import FastAPI, HTTPException
import asyncio
from contextlib import asynccontextmanager
from typing import Dict
from collector import SNMPCollector
from manager import MetricsManager
from model import SystemMetrics

# Configuration
NAS_DEVICES = {
    "wangup": {"host": "192.168.250.139", "name": "SmlNAS-10G"},
    "wangup26": {"host": "192.168.250.182", "name": "BigNAS-10G"},  # enable when SNMP is configured
}

import os

SNMP_PORT = 161
SNMP_USER = "wangup"
SNMP_AUTH = "wanguplovesnmp"

# Sampling interval in seconds (override with env var SNMP_INTERVAL=1 for high-resolution benchmarks)
SNMP_INTERVAL = float(os.environ.get("SNMP_INTERVAL", "2.0"))

# Instances
managers: Dict[str, MetricsManager] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = []
    for key, cfg in NAS_DEVICES.items():
        try:
            collector = SNMPCollector(cfg["host"], SNMP_PORT, SNMP_USER, SNMP_AUTH)
            mgr = MetricsManager(collector, interval=SNMP_INTERVAL)
            managers[key] = mgr
            tasks.append(asyncio.create_task(mgr.start()))
            print(f"[startup] Started monitoring for {key} ({cfg['host']}) at {SNMP_INTERVAL}s interval")
        except Exception as e:
            print(f"[startup] FAILED to init {key} ({cfg['host']}): {e} — skipping")
    
    yield
    
    for mgr in managers.values():
        mgr._running = False
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

app = FastAPI(title="Synology Multi-NAS Monitor API", lifespan=lifespan)

@app.get("/metrics/{device_key}", response_model=SystemMetrics)
async def get_metrics(device_key: str):
    if device_key not in managers:
        raise HTTPException(status_code=404, detail=f"Device {device_key} not found. Available: {list(managers.keys())}")
    
    mgr = managers[device_key]
    if not mgr.current_data:
        raise HTTPException(status_code=503, detail="Metrics not yet available")
    return mgr.current_data

@app.get("/metrics/{device_key}/avg/1m", response_model=SystemMetrics)
async def get_metrics_avg_1m(device_key: str):
    if device_key not in managers:
        raise HTTPException(status_code=404, detail="Device not found")
        
    mgr = managers[device_key]
    if not mgr.avg_1m_data:
        raise HTTPException(status_code=503, detail="Averaged metrics not yet available (wait 1 min)")
    return mgr.avg_1m_data

@app.get("/summary")
async def get_summary():
    result = {}
    for key, mgr in managers.items():
        if mgr.current_data:
            result[key] = {
                "name": NAS_DEVICES[key]["name"],
                "status": "online",
                "write_mb_s": sum(io.write_mb_s for io in mgr.current_data.storage_io) if mgr.current_data.storage_io else 0,
                "read_mb_s": sum(io.read_mb_s for io in mgr.current_data.storage_io) if mgr.current_data.storage_io else 0,
                "peak_load": max(io.load_1min_pct for io in mgr.current_data.storage_io) if mgr.current_data.storage_io else 0
            }
        else:
            result[key] = {"status": "offline/pending"}
    return result

from pydantic import BaseModel

class EventRequest(BaseModel):
    name: str

@app.post("/metrics/{device_key}/event")
async def post_event(device_key: str, event: EventRequest):
    if device_key not in managers:
        raise HTTPException(status_code=404, detail="Device not found")
    
    managers[device_key].record_event(event.name)
    return {"status": "event_recorded", "event": event.name, "device": device_key}

@app.get("/health")
async def health():
    return {key: {"status": "ok", "samples": len(mgr.history)} for key, mgr in managers.items()}


def _prom_gauge(name: str, help_text: str, rows: list[tuple]) -> str:
    """Build a single Prometheus gauge block.
    rows: list of (label_dict, value) — value=None means skip.
    """
    lines = [f"# HELP {name} {help_text}", f"# TYPE {name} gauge"]
    for labels, value in rows:
        if value is None:
            continue
        label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
        lines.append(f"{name}{{{label_str}}} {value}")
    return "\n".join(lines)


@app.get("/prom", response_class=__import__("fastapi").responses.PlainTextResponse)
async def prometheus_metrics():
    """Prometheus text-format endpoint. Point Grafana's Prometheus datasource here."""
    blocks = []

    for device_key, mgr in managers.items():
        m = mgr.current_data
        if not m:
            continue
        d = {"device": device_key}

        # --- system-level ---
        def _num(val):
            try:
                return float(str(val).rstrip("%°C W RPM").split()[0])
            except (ValueError, AttributeError, IndexError):
                return None

        blocks.append(_prom_gauge("nas_cpu_util_pct",      "CPU utilization %",              [(d, _num(m.cpu_util))]))
        blocks.append(_prom_gauge("nas_mem_util_pct",      "Memory utilization % (DSM)",     [(d, _num(m.mem_util))]))
        blocks.append(_prom_gauge("nas_mem_total_mb",      "Total physical RAM MB",          [(d, m.mem_total_mb)]))
        blocks.append(_prom_gauge("nas_mem_avail_mb",      "Available RAM MB",               [(d, m.mem_avail_mb)]))
        blocks.append(_prom_gauge("nas_temp_celsius",      "System temperature °C",          [(d, _num(m.temp))]))
        blocks.append(_prom_gauge("nas_fan_sys_rpm",       "System fan RPM",                 [(d, _num(m.fan_sys))]))
        blocks.append(_prom_gauge("nas_fan_cpu_rpm",       "CPU fan RPM",                    [(d, _num(m.fan_cpu))]))
        blocks.append(_prom_gauge("nas_power_watts",       "Power consumption W",            [(d, _num(m.power))]))

        # --- per-core CPU ---
        blocks.append(_prom_gauge(
            "nas_core_util_pct", "Per-core CPU utilization %",
            [({**d, "core": str(i)}, v) for i, v in enumerate(m.cores_util)]
        ))

        # --- network ---
        blocks.append(_prom_gauge(
            "nas_net_rx_mb_s", "Network receive MiB/s",
            [({**d, "iface": n.name}, n.rx_mb_s) for n in m.network]
        ))
        blocks.append(_prom_gauge(
            "nas_net_tx_mb_s", "Network transmit MiB/s",
            [({**d, "iface": n.name}, n.tx_mb_s) for n in m.network]
        ))

        # --- storage I/O ---
        blocks.append(_prom_gauge(
            "nas_io_load_1min_pct", "Disk I/O load 1-min average %",
            [({**d, "disk": s.device}, s.load_1min_pct) for s in m.storage_io]
        ))
        blocks.append(_prom_gauge(
            "nas_io_load_5min_pct", "Disk I/O load 5-min average %",
            [({**d, "disk": s.device}, s.load_5min_pct) for s in m.storage_io]
        ))
        blocks.append(_prom_gauge(
            "nas_io_read_mb_s", "Disk read throughput MiB/s",
            [({**d, "disk": s.device}, s.read_mb_s) for s in m.storage_io]
        ))
        blocks.append(_prom_gauge(
            "nas_io_write_mb_s", "Disk write throughput MiB/s",
            [({**d, "disk": s.device}, s.write_mb_s) for s in m.storage_io]
        ))
        blocks.append(_prom_gauge(
            "nas_io_read_iops", "Disk read IOPS",
            [({**d, "disk": s.device}, s.r_iops) for s in m.storage_io]
        ))
        blocks.append(_prom_gauge(
            "nas_io_write_iops", "Disk write IOPS",
            [({**d, "disk": s.device}, s.w_iops) for s in m.storage_io]
        ))

        # --- volumes ---
        blocks.append(_prom_gauge(
            "nas_volume_used_mb", "Volume used MB",
            [({**d, "volume": v.name}, v.used_mb) for v in m.volumes]
        ))
        blocks.append(_prom_gauge(
            "nas_volume_total_mb", "Volume total MB",
            [({**d, "volume": v.name}, v.total_mb) for v in m.volumes]
        ))
        blocks.append(_prom_gauge(
            "nas_volume_usage_pct", "Volume usage %",
            [({**d, "volume": v.name}, v.percentage) for v in m.volumes]
        ))

        # --- disks (physical) ---
        blocks.append(_prom_gauge(
            "nas_disk_temp_celsius", "Physical disk temperature °C",
            [({**d, "disk": dk.id, "name": dk.name}, dk.temp) for dk in m.disks]
        ))
        blocks.append(_prom_gauge(
            "nas_disk_remain_life_pct", "SSD remaining life %",
            [({**d, "disk": dk.id, "name": dk.name}, dk.remain_life) for dk in m.disks]
        ))
        blocks.append(_prom_gauge(
            "nas_disk_bad_sectors", "Disk bad sector count",
            [({**d, "disk": dk.id, "name": dk.name}, dk.bad_sectors) for dk in m.disks]
        ))

    return "\n\n".join(blocks) + "\n"


if __name__ == "__main__":
    import uvicorn
    # Use port 7003 as previously set by user
    uvicorn.run(app, host="0.0.0.0", port=7003)
