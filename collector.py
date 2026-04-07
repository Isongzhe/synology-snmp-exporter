import time
from ezsnmp import Session
from ezsnmp.exceptions import GenericError
from typing import Dict, List, Any, Optional

class SNMPCollector:
    def __init__(self, host: str, port: int, user: str, auth: str, auth_proto: str = "SHA"):
        self.host = host
        self.port = port
        self.user = user
        self.auth = auth
        self.auth_proto = auth_proto
        
        # OID Definitions (Condensed for the class)
        self.OIDS = {
            "SYS_MODEL": "1.3.6.1.4.1.6574.1.5.1.0",
            "SYS_TEMP": "1.3.6.1.4.1.6574.1.2.0",
            "SYS_POWER": "1.3.6.1.4.1.6574.1.3.0",
            "FAN_SYS": "1.3.6.1.4.1.6574.1.4.1.0",
            "FAN_CPU": "1.3.6.1.4.1.6574.1.4.2.0",
            "CPU_UTIL": "1.3.6.1.4.1.6574.1.7.1.0",
            "MEM_UTIL": "1.3.6.1.4.1.6574.1.7.2.0",
            # memTotalReal / memAvailReal: from UCD-SNMP-MIB (net-snmp standard MIB).
            # These reflect Linux kernel-level physical memory (RAM), reported in KB.
            # Different from MEM_UTIL above, which is Synology DSM's own application-layer
            # memory usage %. The two values may differ because the kernel uses spare RAM
            # as disk cache (page cache), making kernel-reported usage appear higher than
            # what DSM considers "in use by applications".
            "MEM_TOTAL": "1.3.6.1.4.1.2021.4.5.0",      # memTotalReal: total physical RAM (KB)
            "MEM_AVAIL": "1.3.6.1.4.1.2021.4.6.0",      # memAvailReal: free RAM available for new processes (KB)
            "HR_CPU": "1.3.6.1.2.1.25.3.3.1.2",
            "STOR_TYPE": "1.3.6.1.2.1.25.2.3.1.2",
            "STOR_DESCR": "1.3.6.1.2.1.25.2.3.1.3",
            "STOR_UNITS": "1.3.6.1.2.1.25.2.3.1.4",
            "STOR_SIZE": "1.3.6.1.2.1.25.2.3.1.5",
            "STOR_USED": "1.3.6.1.2.1.25.2.3.1.6",
            "RAID_NAME": "1.3.6.1.4.1.6574.3.1.1.2",
            "RAID_STATUS": "1.3.6.1.4.1.6574.3.1.1.3",
            "RAID_FREE": "1.3.6.1.4.1.6574.3.1.1.4",
            "RAID_TOTAL": "1.3.6.1.4.1.6574.3.1.1.5",
            "DISK_ID": "1.3.6.1.4.1.6574.2.1.1.2",
            "DISK_MODEL": "1.3.6.1.4.1.6574.2.1.1.3",
            "DISK_TYPE": "1.3.6.1.4.1.6574.2.1.1.4",
            "DISK_STAT": "1.3.6.1.4.1.6574.2.1.1.5",
            "DISK_TEMP": "1.3.6.1.4.1.6574.2.1.1.6",
            "DISK_ROLE": "1.3.6.1.4.1.6574.2.1.1.7",
            "DISK_RETRY": "1.3.6.1.4.1.6574.2.1.1.8",
            "DISK_BADSEC": "1.3.6.1.4.1.6574.2.1.1.9",
            "DISK_IDFAIL": "1.3.6.1.4.1.6574.2.1.1.10",
            "DISK_LIFE": "1.3.6.1.4.1.6574.2.1.1.11",
            "DISK_NAME": "1.3.6.1.4.1.6574.2.1.1.12",
            "DISK_HEALTH": "1.3.6.1.4.1.6574.2.1.1.13",
            "STIO_DEV": "1.3.6.1.4.1.6574.101.1.1.2",
            # storageIOLA: disk I/O load percentage (how busy the disk is, 0-100%).
            # OID .7 would be "instant" load but is absent on this NAS model.
            # OID .8 = LA1 (Load Average 1-minute): smoothed average over last 1 minute.
            # OID .9 = LA5 (Load Average 5-minute): smoothed average over last 5 minutes.
            # LA (Load Average) is the same concept as Linux CPU load average — a smoothed
            # rolling average that dampens short spikes. Higher LA = disk was busier recently.
            "STIO_LA1": "1.3.6.1.4.1.6574.101.1.1.8",   # LA1: 1-min avg disk load %
            "STIO_LA5": "1.3.6.1.4.1.6574.101.1.1.9",   # LA5: 5-min avg disk load %
            # storageIONRead / storageIONWritten: cumulative byte counters (64-bit).
            # These are ever-increasing counters — we take the delta between two snapshots
            # and divide by elapsed seconds to get MiB/s throughput.
            # 64-bit (vs 32-bit) means they won't wrap/overflow even on high-throughput NAS.
            "STIO_READX": "1.3.6.1.4.1.6574.101.1.1.12",  # storageIONRead: total bytes read (cumulative)
            "STIO_WRITX": "1.3.6.1.4.1.6574.101.1.1.13",  # storageIONWritten: total bytes written (cumulative)
            # storageIOReads / storageIOWrites: cumulative I/O operation counters.
            # Delta / elapsed = IOPS (I/O Operations Per Second).
            "STIO_READS": "1.3.6.1.4.1.6574.101.1.1.5",   # storageIOReads: total read ops (cumulative)
            "STIO_WRITES": "1.3.6.1.4.1.6574.101.1.1.6",  # storageIOWrites: total write ops (cumulative)
            # Network interface OIDs — from standard IF-MIB / IF-MIB extensions.
            # These apply to each network interface (eth0, bond0, etc.) indexed by ifIndex.
            "IF_DESCR": "1.3.6.1.2.1.2.2.1.2",            # ifDescr: interface name (e.g. "eth0")
            "IF_STATUS": "1.3.6.1.2.1.2.2.1.8",           # ifOperStatus: link state (1=UP, 2=DOWN)
            # HC = High Capacity: 64-bit byte counters (same overflow-safe reason as STIO above).
            "IF_HC_IN": "1.3.6.1.2.1.31.1.1.1.6",         # ifHCInOctets: total bytes received (cumulative)
            "IF_HC_OUT": "1.3.6.1.2.1.31.1.1.1.10",       # ifHCOutOctets: total bytes sent (cumulative)
            # ifHighSpeed: interface speed in Mbps (megabits per second).
            # e.g. 1000 = 1 GbE, 10000 = 10 GbE. Used for display only, not throughput calc.
            "IF_SPEED": "1.3.6.1.2.1.31.1.1.1.15",        # ifHighSpeed: link speed in Mbps
        }
        
    def _make_session(self) -> Session:
        return Session(
            hostname=self.host,
            port_number=self.port,
            version=3,
            security_level="authNoPriv",
            security_username=self.user,
            auth_protocol=self.auth_proto,
            auth_passphrase=self.auth,
        )

    def _g(self, session, oid):
        try:
            return session.get(oid)[0].value
        except Exception:
            return None

    def _w(self, session, oid):
        try:
            return session.walk(oid)
        except Exception:
            return []

    def _si(self, v, d=0):
        try:
            return int(str(v))
        except Exception:
            return d

    def fetch_metrics(self) -> Dict[str, Any]:
        session = self._make_session()
        
        # 1. System
        model = self._g(session, self.OIDS["SYS_MODEL"])
        temp = self._g(session, self.OIDS["SYS_TEMP"])
        power = self._g(session, self.OIDS["SYS_POWER"])
        fan_sys = self._g(session, self.OIDS["FAN_SYS"])
        fan_cpu = self._g(session, self.OIDS["FAN_CPU"])
        cpu_util = self._g(session, self.OIDS["CPU_UTIL"])
        mem_util = self._g(session, self.OIDS["MEM_UTIL"])
        # Raw values are in KB; converted to MB in the return dict below.
        # mem_avail_mb is the more useful metric for monitoring: it shows how much RAM
        # the OS can actually give to a new process (e.g. a Zarr benchmark job).
        mem_total_kb = self._si(self._g(session, self.OIDS["MEM_TOTAL"]))
        mem_avail_kb = self._si(self._g(session, self.OIDS["MEM_AVAIL"]))
        cores = [self._si(v.value) for v in self._w(session, self.OIDS["HR_CPU"])]
        
        # 2. Volumes
        types = {v.index: v.value for v in self._w(session, self.OIDS["STOR_TYPE"])}
        descrs = {v.index: v.value for v in self._w(session, self.OIDS["STOR_DESCR"])}
        units = {v.index: self._si(v.value) for v in self._w(session, self.OIDS["STOR_UNITS"])}
        sizes = {v.index: self._si(v.value) for v in self._w(session, self.OIDS["STOR_SIZE"])}
        used_map = {v.index: self._si(v.value) for v in self._w(session, self.OIDS["STOR_USED"])}
        volumes = []
        for idx, typ in types.items():
            if ".25.2.1.4" not in str(typ): continue
            alloc = units.get(idx, 1)
            size_b = sizes.get(idx, 0) * alloc
            used_b = used_map.get(idx, 0) * alloc
            volumes.append({
                "name": str(descrs.get(idx, idx)),
                "used_mb": used_b // (1024*1024),
                "total_mb": size_b // (1024*1024),
                "percentage": round(used_b / size_b * 100, 1) if size_b else 0
            })

        # 3. RAID
        raid_names = {v.index: v.value for v in self._w(session, self.OIDS["RAID_NAME"])}
        raid_stats = {v.index: v.value for v in self._w(session, self.OIDS["RAID_STATUS"])}
        raid_free = {v.index: self._si(v.value) for v in self._w(session, self.OIDS["RAID_FREE"])}
        raid_total = {v.index: self._si(v.value) for v in self._w(session, self.OIDS["RAID_TOTAL"])}
        raids = []
        for idx, name in raid_names.items():
            total = raid_total.get(idx, 0)
            free = raid_free.get(idx, 0)
            raids.append({
                "name": str(name),
                "status": str(raid_stats.get(idx, "?")),
                "used_gb": (total - free) // (1024*1024*1024),
                "total_gb": total // (1024*1024*1024),
                "percentage": round((total - free) / total * 100, 1) if total else 0
            })

        # 4. Disks
        disk_ids = {v.index: v.value for v in self._w(session, self.OIDS["DISK_ID"])}
        disk_models = {v.index: v.value for v in self._w(session, self.OIDS["DISK_MODEL"])}
        disk_types = {v.index: v.value for v in self._w(session, self.OIDS["DISK_TYPE"])}
        disk_stats = {v.index: v.value for v in self._w(session, self.OIDS["DISK_STAT"])}
        disk_temps = {v.index: self._si(v.value) for v in self._w(session, self.OIDS["DISK_TEMP"])}
        disk_roles = {v.index: v.value for v in self._w(session, self.OIDS["DISK_ROLE"])}
        disk_retry = {v.index: self._si(v.value) for v in self._w(session, self.OIDS["DISK_RETRY"])}
        disk_badsec = {v.index: self._si(v.value) for v in self._w(session, self.OIDS["DISK_BADSEC"])}
        disk_idfail = {v.index: self._si(v.value) for v in self._w(session, self.OIDS["DISK_IDFAIL"])}
        disk_life = {v.index: self._si(v.value) for v in self._w(session, self.OIDS["DISK_LIFE"])}
        disk_names = {v.index: v.value for v in self._w(session, self.OIDS["DISK_NAME"])}
        disk_health = {v.index: v.value for v in self._w(session, self.OIDS["DISK_HEALTH"])}
        disks = []
        for idx, did in disk_ids.items():
            disks.append({
                "id": str(did),
                "name": str(disk_names.get(idx, "")),
                "model": str(disk_models.get(idx, "?")),
                "type": str(disk_types.get(idx, "?")),
                "status": str(disk_stats.get(idx, "?")),
                "health": str(disk_health.get(idx, "?")),
                "role": str(disk_roles.get(idx, "?")),
                "temp": disk_temps.get(idx),
                "remain_life": disk_life.get(idx),
                "retries": disk_retry.get(idx, 0),
                "bad_sectors": disk_badsec.get(idx, 0),
                "ident_fails": disk_idfail.get(idx, 0)
            })

        # 5. IO & Network Counters (raw values)
        io_raw = {
            "dev": {v.index: v.value for v in self._w(session, self.OIDS["STIO_DEV"])},
            "la1": {v.index: self._si(v.value) for v in self._w(session, self.OIDS["STIO_LA1"])},  # 1-min avg
            "la5": {v.index: self._si(v.value) for v in self._w(session, self.OIDS["STIO_LA5"])},  # 5-min avg
            "rx": {v.index: self._si(v.value) for v in self._w(session, self.OIDS["STIO_READX"])},
            "tx": {v.index: self._si(v.value) for v in self._w(session, self.OIDS["STIO_WRITX"])},
            "ops_r": {v.index: self._si(v.value) for v in self._w(session, self.OIDS["STIO_READS"])},
            "ops_w": {v.index: self._si(v.value) for v in self._w(session, self.OIDS["STIO_WRITES"])}
        }
        
        net_raw = {
            "desc": {v.index: v.value for v in self._w(session, self.OIDS["IF_DESCR"])},
            "stat": {v.index: v.value for v in self._w(session, self.OIDS["IF_STATUS"])},
            "spd": {v.index: self._si(v.value) for v in self._w(session, self.OIDS["IF_SPEED"])},
            "rx": {v.index: self._si(v.value) for v in self._w(session, self.OIDS["IF_HC_IN"])},
            "tx": {v.index: self._si(v.value) for v in self._w(session, self.OIDS["IF_HC_OUT"])}
        }

        return {
            "system": {
                "model": model, "temp": temp, "power": power,
                "fan_sys": fan_sys, "fan_cpu": fan_cpu,
                "cpu_util": cpu_util, "mem_util": mem_util,
                "mem_total_mb": mem_total_kb // 1024 if mem_total_kb else None,
                "mem_avail_mb": mem_avail_kb // 1024 if mem_avail_kb else None,
                "cores": cores
            },
            "volumes": volumes,
            "raids": raids,
            "disks": disks,
            "io_raw": io_raw,
            "net_raw": net_raw,
            "timestamp": time.monotonic()
        }
