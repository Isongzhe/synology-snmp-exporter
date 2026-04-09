from pydantic import BaseModel
from typing import List, Dict, Optional

class DiskMetric(BaseModel):
    id: str
    name: str
    model: str
    type: str
    status: str
    health: str
    role: str
    temp: Optional[int]
    remain_life: Optional[int]
    retries: int
    bad_sectors: int
    ident_fails: int

class VolumeMetric(BaseModel):
    name: str
    used_mb: int
    total_mb: int
    percentage: float

class RaidMetric(BaseModel):
    name: str
    status: str
    used_gb: int
    total_gb: int
    percentage: float

class NetworkMetric(BaseModel):
    name: str
    status: str
    speed_mbps: int
    rx_mb_s: float
    tx_mb_s: float

class StorageIOMetric(BaseModel):
    device: str
    # load_1min_pct / load_5min_pct: disk I/O load percentage (0-100%).
    # These are Load Average (LA) values — a smoothed rolling average of how busy the disk is.
    # LA1 reacts faster to changes; LA5 is smoother and shows sustained load trends.
    # Note: "instant" load (OID .7) is not available on this NAS, so LA1 is the fastest
    # resolution we can get. Values come from Synology StorageIO MIB (.1.3.6.1.4.1.6574.101).
    load_1min_pct: int   # LA1: 1-minute load average %
    load_5min_pct: int   # LA5: 5-minute load average %
    # Throughput in MiB/s (mebibytes per second, 1 MiB = 1024*1024 bytes).
    # Calculated as: delta_bytes / elapsed_seconds / 1048576
    read_mb_s: float
    write_mb_s: float
    # IOPS: I/O Operations Per Second (number of read/write requests per second)
    r_iops: float
    w_iops: float

class SystemMetrics(BaseModel):
    time: str
    elapsed: float
    model: Optional[str]
    temp: Optional[str]
    power: Optional[str]
    fan_sys: Optional[str]
    fan_cpu: Optional[str]
    cpu_util: Optional[str]
    cores_util: List[int]
    mem_util: Optional[str]       # DSM application-layer memory usage % (Synology's own metric)
    # mem_total_mb / mem_avail_mb: Linux kernel-level physical RAM, from UCD-SNMP-MIB.
    # mem_avail_mb is the practical limit for new processes — use this for OOM (Out of Memory)
    # risk assessment during heavy workloads (e.g. Zarr benchmark, ML data loading).
    mem_total_mb: Optional[int] = None   # total physical RAM in MB
    mem_avail_mb: Optional[int] = None   # free RAM available for new allocations in MB
    volumes: List[VolumeMetric]
    raids: List[RaidMetric]
    disks: List[DiskMetric]
    storage_io: List[StorageIOMetric]
    network: List[NetworkMetric]
