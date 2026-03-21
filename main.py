import time
from ezsnmp import Session
from ezsnmp.exceptions import GenericError

NAS_HOST = "192.168.250.139"
NAS_PORT = 161
SNMP_USER = "wangup"
SNMP_AUTH = "wanguplovesnmp"
AUTH_PROTO = "SHA"

OID_CPU_USER = "1.3.6.1.4.1.2021.11.9.0"
OID_CPU_SYS = "1.3.6.1.4.1.2021.11.10.0"
OID_CPU_IDLE = "1.3.6.1.4.1.2021.11.11.0"
OID_HR_CPU = "1.3.6.1.2.1.25.3.3.1.2"
OID_MEM_TOTAL = "1.3.6.1.4.1.2021.4.5.0"
OID_MEM_AVAIL = "1.3.6.1.4.1.2021.4.6.0"
OID_STOR_TYPE = "1.3.6.1.2.1.25.2.3.1.2"
OID_STOR_DESCR = "1.3.6.1.2.1.25.2.3.1.3"
OID_STOR_UNITS = "1.3.6.1.2.1.25.2.3.1.4"
OID_STOR_SIZE = "1.3.6.1.2.1.25.2.3.1.5"
OID_STOR_USED = "1.3.6.1.2.1.25.2.3.1.6"
OID_DISK_ID = "1.3.6.1.4.1.6574.2.1.1.2"
OID_DISK_MODEL = "1.3.6.1.4.1.6574.2.1.1.3"
OID_DISK_TYPE = "1.3.6.1.4.1.6574.2.1.1.4"
OID_DISK_STAT = "1.3.6.1.4.1.6574.2.1.1.5"  # 1=Normal 5=Crashed
OID_DISK_TEMP = "1.3.6.1.4.1.6574.2.1.1.6"
OID_DISK_ROLE = "1.3.6.1.4.1.6574.2.1.1.7"  # data/hotspare/ssd_cache/none
OID_DISK_RETRY = "1.3.6.1.4.1.6574.2.1.1.8"
OID_DISK_BADSEC = "1.3.6.1.4.1.6574.2.1.1.9"
OID_DISK_IDFAIL = "1.3.6.1.4.1.6574.2.1.1.10"
OID_DISK_LIFE = "1.3.6.1.4.1.6574.2.1.1.11"  # % remaining life (SSD)
OID_DISK_NAME = "1.3.6.1.4.1.6574.2.1.1.12"  # kernel device name e.g. sda
OID_DISK_HEALTH = "1.3.6.1.4.1.6574.2.1.1.13"  # 1=Normal 2=Warning 3=Critical 4=Failing
DISK_STATUS = {
    "1": "Normal",
    "2": "Initialized",
    "3": "NotInit",
    "4": "SysPartFail",
    "5": "Crashed",
}
DISK_HEALTH = {"1": "Normal", "2": "Warning", "3": "Critical", "4": "Failing"}

# Synology StorageIO MIB (1.3.6.1.4.1.6574.101.1.1)
OID_STIO_DEV = "1.3.6.1.4.1.6574.101.1.1.2"
OID_STIO_LA = "1.3.6.1.4.1.6574.101.1.1.7"  # current load %
OID_STIO_LA1 = "1.3.6.1.4.1.6574.101.1.1.8"  # 1-min load %
OID_STIO_READX = "1.3.6.1.4.1.6574.101.1.1.11"  # 64-bit bytes read since boot
OID_STIO_WRITX = "1.3.6.1.4.1.6574.101.1.1.12"  # 64-bit bytes written since boot
OID_STIO_READS = "1.3.6.1.4.1.6574.101.1.1.5"  # read ops since boot
OID_STIO_WRITES = "1.3.6.1.4.1.6574.101.1.1.6"  # write ops since boot

# Synology System MIB (1.3.6.1.4.1.6574.1)
OID_SYS_MODEL = "1.3.6.1.4.1.6574.1.5.1.0"
OID_SYS_TEMP = "1.3.6.1.4.1.6574.1.2.0"
OID_SYS_POWER = "1.3.6.1.4.1.6574.1.3.0"
OID_FAN_SYS = "1.3.6.1.4.1.6574.1.4.1.0"
OID_FAN_CPU = "1.3.6.1.4.1.6574.1.4.2.0"
OID_CPU_UTIL = "1.3.6.1.4.1.6574.1.7.1.0"  # Synology CPU utilization %
OID_MEM_UTIL = "1.3.6.1.4.1.6574.1.7.2.0"  # Synology memory utilization %

# Synology RAID MIB (1.3.6.1.4.1.6574.3.1.1)
OID_RAID_NAME = "1.3.6.1.4.1.6574.3.1.1.2"
OID_RAID_STATUS = "1.3.6.1.4.1.6574.3.1.1.3"
OID_RAID_FREE = "1.3.6.1.4.1.6574.3.1.1.4"
OID_RAID_TOTAL = "1.3.6.1.4.1.6574.3.1.1.5"
RAID_STATUS = {
    "1": "Normal",
    "2": "Repairing",
    "3": "Migrating",
    "4": "Expanding",
    "5": "Deleting",
    "6": "Creating",
    "7": "Syncing",
    "8": "ParityCheck",
    "9": "Assembling",
    "10": "Canceling",
    "11": "Degrade",
    "12": "Crashed",
}
OID_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
OID_IF_STATUS = "1.3.6.1.2.1.2.2.1.8"
OID_IF_HC_IN = "1.3.6.1.2.1.31.1.1.1.6"
OID_IF_HC_OUT = "1.3.6.1.2.1.31.1.1.1.10"
OID_IF_SPEED = "1.3.6.1.2.1.31.1.1.1.15"


def make_session() -> Session:
    return Session(
        hostname=NAS_HOST,
        port_number=NAS_PORT,
        version=3,
        security_level="authNoPriv",
        security_username=SNMP_USER,
        auth_protocol=AUTH_PROTO,
        auth_passphrase=SNMP_AUTH,
    )


def g(session, oid):
    try:
        return session.get(oid).value
    except GeneratorExit:
        return None
    except Exception:
        return None


def w(session, oid):
    try:
        return session.walk(oid)
    except Exception:
        return []


def si(v, d=0):
    try:
        return int(str(v))
    except Exception:
        return d


def main():
    session = make_session()
    net_prev = {}
    stio_prev = {}
    t_prev = time.monotonic()

    while True:
        t_now = time.monotonic()
        elapsed = t_now - t_prev
        t_prev = t_now

        print("=" * 60)
        print(f"time={time.strftime('%H:%M:%S')}  elapsed={elapsed:.2f}s")

        # System (Synology MIB — may be empty if SNMP user lacks access to 1.3.6.1.4.1.6574.1)
        model = g(session, OID_SYS_MODEL)
        temp = g(session, OID_SYS_TEMP)
        power = g(session, OID_SYS_POWER)
        fan_sys = g(session, OID_FAN_SYS)
        fan_cpu = g(session, OID_FAN_CPU)
        cpu_util = g(session, OID_CPU_UTIL)
        mem_util = g(session, OID_MEM_UTIL)
        cores = [si(v.value) for v in w(session, OID_HR_CPU)]
        sysline = (
            f"Model: {model or '(no access)'}  Temp: {temp or '?'}C  "
            f"Power: {'OK' if power == '1' else 'FAIL' if power else '?'}  "
            f"Fan(sys/cpu): {'OK' if fan_sys == '1' else 'FAIL' if fan_sys else '?'}/"
            f"{'OK' if fan_cpu == '1' else 'FAIL' if fan_cpu else '?'}"
        )
        print(sysline)
        cpu_str = f"{cpu_util}%" if cpu_util else f"(per-core only)"
        mem_str = f"{mem_util}%" if mem_util else "(no access)"
        print(f"CPU: {cpu_str}  cores={cores}")
        print(f"RAM: {mem_str}")

        # Storage volumes (hrStorage fixed disks)
        types = {v.index: v.value for v in w(session, OID_STOR_TYPE)}
        descrs = {v.index: v.value for v in w(session, OID_STOR_DESCR)}
        units = {v.index: si(v.value) for v in w(session, OID_STOR_UNITS)}
        sizes = {v.index: si(v.value) for v in w(session, OID_STOR_SIZE)}
        used_map = {v.index: si(v.value) for v in w(session, OID_STOR_USED)}
        print("Volumes:")
        for idx, typ in types.items():
            if ".25.2.1.4" not in str(typ):  # hrStorageFixedDisk (iso. or 1. prefix)
                continue
            alloc = units.get(idx, 1)
            size_b = sizes.get(idx, 0) * alloc
            used_b = used_map.get(idx, 0) * alloc
            pct = used_b / size_b * 100 if size_b else 0
            print(
                f"  {descrs.get(idx, idx)}: {used_b // 1024 // 1024}MB / {size_b // 1024 // 1024}MB ({pct:.1f}%)"
            )

        # RAID
        raid_names = {v.index: v.value for v in w(session, OID_RAID_NAME)}
        raid_stats = {v.index: v.value for v in w(session, OID_RAID_STATUS)}
        raid_free = {v.index: si(v.value) for v in w(session, OID_RAID_FREE)}
        raid_total = {v.index: si(v.value) for v in w(session, OID_RAID_TOTAL)}
        if raid_names:
            print("RAID:")
            for idx in raid_names:
                st = RAID_STATUS.get(str(raid_stats.get(idx)), "?")
                total = raid_total.get(idx, 0)
                free = raid_free.get(idx, 0)
                pct = (total - free) / total * 100 if total else 0
                print(
                    f"  {raid_names[idx]}: {st}  {(total - free) // 1024 // 1024 // 1024}GB / {total // 1024 // 1024 // 1024}GB ({pct:.1f}%)"
                )

        # StorageIO snapshot
        stio_dev = {v.index: v.value for v in w(session, OID_STIO_DEV)}
        stio_la = {v.index: si(v.value) for v in w(session, OID_STIO_LA)}
        stio_la1 = {v.index: si(v.value) for v in w(session, OID_STIO_LA1)}
        stio_readx = {v.index: si(v.value) for v in w(session, OID_STIO_READX)}
        stio_writx = {v.index: si(v.value) for v in w(session, OID_STIO_WRITX)}
        stio_reads = {v.index: si(v.value) for v in w(session, OID_STIO_READS)}
        stio_writes = {v.index: si(v.value) for v in w(session, OID_STIO_WRITES)}

        # Physical disks
        disk_ids = {v.index: v.value for v in w(session, OID_DISK_ID)}
        disk_models = {v.index: v.value for v in w(session, OID_DISK_MODEL)}
        disk_types = {v.index: v.value for v in w(session, OID_DISK_TYPE)}
        disk_stats = {v.index: v.value for v in w(session, OID_DISK_STAT)}
        disk_temps = {v.index: si(v.value) for v in w(session, OID_DISK_TEMP)}
        disk_roles = {v.index: v.value for v in w(session, OID_DISK_ROLE)}
        disk_retry = {v.index: si(v.value) for v in w(session, OID_DISK_RETRY)}
        disk_badsec = {v.index: si(v.value) for v in w(session, OID_DISK_BADSEC)}
        disk_idfail = {v.index: si(v.value) for v in w(session, OID_DISK_IDFAIL)}
        disk_life = {v.index: si(v.value) for v in w(session, OID_DISK_LIFE)}
        disk_names = {v.index: v.value for v in w(session, OID_DISK_NAME)}
        disk_health = {v.index: v.value for v in w(session, OID_DISK_HEALTH)}
        print("Disks:")
        for idx in disk_ids:
            st = DISK_STATUS.get(str(disk_stats.get(idx)), "?")
            hlth = DISK_HEALTH.get(str(disk_health.get(idx)), "?")
            dname = str(disk_names.get(idx, ""))
            print(
                f"  {disk_ids[idx]} [{dname}]  {disk_models.get(idx, '?')}  {disk_types.get(idx, '?')}"
            )
            print(
                f"\t status={st}  health={hlth}  role={disk_roles.get(idx, '?')}  temp={disk_temps.get(idx, '?')}C  remain_life={disk_life.get(idx, '?')}%"
            )
            print(
                f"\t retries={disk_retry.get(idx, '?')}  bad_sectors={disk_badsec.get(idx, '?')}  ident_fails={disk_idfail.get(idx, '?')}"
            )

        # StorageIO (per kernel device: sata1, sata2, ...)
        if stio_dev:
            print("StorageIO:")
            for sidx, sdev in stio_dev.items():
                rx = stio_readx.get(sidx, 0)
                tx = stio_writx.get(sidx, 0)
                ops_r = stio_reads.get(sidx, 0)
                ops_w = stio_writes.get(sidx, 0)
                rx_bps = tx_bps = ops_r_s = ops_w_s = 0.0
                if sidx in stio_prev and elapsed > 0:
                    p = stio_prev[sidx]
                    rx_bps = max(0, rx - p[0]) * 8 / elapsed
                    tx_bps = max(0, tx - p[1]) * 8 / elapsed
                    ops_r_s = max(0, ops_r - p[2]) / elapsed
                    ops_w_s = max(0, ops_w - p[3]) / elapsed
                stio_prev[sidx] = (rx, tx, ops_r, ops_w)
                la = stio_la.get(sidx, 0)
                la1 = stio_la1.get(sidx, 0)
                print(
                    f"  {sdev}: load={la}% (1min={la1}%)  read={rx_bps / 1e6:.2f}MB/s  write={tx_bps / 1e6:.2f}MB/s  r_iops={ops_r_s:.1f}  w_iops={ops_w_s:.1f}"
                )

        # Network
        descrs = {v.index: v.value for v in w(session, OID_IF_DESCR)}
        stats = {v.index: v.value for v in w(session, OID_IF_STATUS)}
        speeds = {v.index: si(v.value) for v in w(session, OID_IF_SPEED)}
        hc_in = {v.index: si(v.value) for v in w(session, OID_IF_HC_IN)}
        hc_out = {v.index: si(v.value) for v in w(session, OID_IF_HC_OUT)}
        print("Network:")
        for idx, name in descrs.items():
            up = stats.get(idx) == "1"
            rx = hc_in.get(idx, 0)
            tx = hc_out.get(idx, 0)
            rx_bps = tx_bps = 0.0
            if idx in net_prev and elapsed > 0:
                rx_bps = max(0, rx - net_prev[idx][0]) * 8 / elapsed
                tx_bps = max(0, tx - net_prev[idx][1]) * 8 / elapsed
            spd = speeds.get(idx, 0)
            print(
                f"  {name}: {'UP' if up else 'dn'}  {spd}Mbps  rx={rx_bps / 1e6:.3f}MB/s  tx={tx_bps / 1e6:.3f}MB/s"
            )
            net_prev[idx] = (rx, tx)

        time.sleep(1.0)


if __name__ == "__main__":
    main()
