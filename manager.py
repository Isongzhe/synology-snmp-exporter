import asyncio
import time
from collections import deque
from typing import Dict, List, Any, Optional
from collector import SNMPCollector
from model import SystemMetrics, VolumeMetric, RaidMetric, DiskMetric, NetworkMetric, StorageIOMetric

class MetricsManager:
    def __init__(self, collector: SNMPCollector, interval: float = 10.0, history_seconds: int = 60):
        self.collector = collector
        self.interval = interval
        self.history = deque(maxlen=int(history_seconds / interval) + 1)
        self.current_data: Optional[SystemMetrics] = None
        self.avg_1m_data: Optional[SystemMetrics] = None
        self._prev_raw = None
        self._running = False

    async def start(self):
        self._running = True
        while self._running:
            try:
                raw = await asyncio.to_thread(self.collector.fetch_metrics)
                processed = self._process_snapshot(raw)
                if processed:
                    self.current_data = processed
                    self.history.append(processed)
                    self._calculate_averages()
            except Exception as e:
                print(f"Collection error: {e}")
            await asyncio.sleep(self.interval)

    def _process_snapshot(self, raw: Dict[str, Any]) -> Optional[SystemMetrics]:
        if not self._prev_raw:
            self._prev_raw = raw
            return None
        
        elapsed = raw["timestamp"] - self._prev_raw["timestamp"]
        if elapsed <= 0: return None
        
        # Calculate IO Rates
        storage_io = []
        total_write_all_disks = 0
        for idx, dev in raw["io_raw"]["dev"].items():
            prev = self._prev_raw["io_raw"]
            if idx in prev["dev"]:
                # Use direct Bytes -> MiB/s calculation for better accuracy
                delta_r = max(0, raw["io_raw"]["rx"].get(idx, 0) - prev["rx"].get(idx, 0))
                delta_w = max(0, raw["io_raw"]["tx"].get(idx, 0) - prev["tx"].get(idx, 0))
                
                # MiB/s = bytes / elapsed / (1024*1024)
                r_mib = (delta_r / elapsed) / 1048576.0
                w_mib = (delta_w / elapsed) / 1048576.0
                
                ops_r = max(0, raw["io_raw"]["ops_r"].get(idx, 0) - prev["ops_r"].get(idx, 0)) / elapsed
                ops_w = max(0, raw["io_raw"]["ops_w"].get(idx, 0) - prev["ops_w"].get(idx, 0)) / elapsed
                
                total_write_all_disks += w_mib
                
                storage_io.append(StorageIOMetric(
                    device=str(dev),
                    load_1min_pct=raw["io_raw"]["la1"].get(idx, 0),
                    load_5min_pct=raw["io_raw"]["la5"].get(idx, 0),
                    read_mb_s=round(r_mib, 2),
                    write_mb_s=round(w_mib, 2),
                    r_iops=round(ops_r, 1),
                    w_iops=round(ops_w, 1)
                ))

        if total_write_all_disks > 10:
            print(f"[DEBUG] High Write detected: {total_write_all_disks:.2f} MiB/s across all disks (elapsed: {elapsed:.2f}s)")

        # Calculate Network Rates
        network = []
        for idx, desc in raw["net_raw"]["desc"].items():
            prev = self._prev_raw["net_raw"]
            if idx in prev["desc"]:
                # Convert bytes to MB/s (decimal for networking usually, but keeping MB/s consistent)
                delta_rx = max(0, raw["net_raw"]["rx"].get(idx, 0) - prev["rx"].get(idx, 0))
                delta_tx = max(0, raw["net_raw"]["tx"].get(idx, 0) - prev["tx"].get(idx, 0))
                
                network.append(NetworkMetric(
                    name=str(desc),
                    status="UP" if raw["net_raw"]["stat"].get(idx) == "1" else "dn",
                    speed_mbps=raw["net_raw"]["spd"].get(idx, 0),
                    rx_mb_s=round((delta_rx / elapsed) / 1e6, 3),
                    tx_mb_s=round((delta_tx / elapsed) / 1e6, 3)
                ))

        self._prev_raw = raw
        
        return SystemMetrics(
            time=time.strftime('%H:%M:%S'),
            elapsed=round(elapsed, 2),
            model=raw["system"]["model"],
            temp=raw["system"]["temp"],
            power=raw["system"]["power"],
            fan_sys=raw["system"]["fan_sys"],
            fan_cpu=raw["system"]["fan_cpu"],
            cpu_util=raw["system"]["cpu_util"],
            cores_util=raw["system"]["cores"],
            mem_util=raw["system"]["mem_util"],
            mem_total_mb=raw["system"].get("mem_total_mb"),
            mem_avail_mb=raw["system"].get("mem_avail_mb"),
            volumes=[VolumeMetric(**v) for v in raw["volumes"]],
            raids=[RaidMetric(**r) for r in raw["raids"]],
            disks=[DiskMetric(**d) for d in raw["disks"]],
            storage_io=storage_io,
            network=network
        )

    def _calculate_averages(self):
        if len(self.history) < 2: return
        
        # We only really need to average throughput and utilization
        # Basic state (Normal/Error) shouldn't be averaged but reflected from latest
        latest = self.history[-1]
        
        # Create a deep copy for averaging
        avg = latest.model_copy()
        
        # Average throughputs for 1 minute
        io_avgs = {}
        for h in self.history:
            for item in h.storage_io:
                if item.device not in io_avgs: io_avgs[item.device] = []
                io_avgs[item.device].append(item)
        
        for item in avg.storage_io:
            history_list = io_avgs.get(item.device, [])
            if history_list:
                item.read_mb_s = round(sum(x.read_mb_s for x in history_list) / len(history_list), 2)
                item.write_mb_s = round(sum(x.write_mb_s for x in history_list) / len(history_list), 2)
                item.r_iops = round(sum(x.r_iops for x in history_list) / len(history_list), 1)
                item.w_iops = round(sum(x.w_iops for x in history_list) / len(history_list), 1)

        # Average network
        net_avgs = {}
        for h in self.history:
            for item in h.network:
                if item.name not in net_avgs: net_avgs[item.name] = []
                net_avgs[item.name].append(item)
        
        for item in avg.network:
            history_list = net_avgs.get(item.name, [])
            if history_list:
                item.rx_mb_s = round(sum(x.rx_mb_s for x in history_list) / len(history_list), 3)
                item.tx_mb_s = round(sum(x.tx_mb_s for x in history_list) / len(history_list), 3)

        self.avg_1m_data = avg
