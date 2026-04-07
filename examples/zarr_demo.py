import logging
import time
import threading
import numpy as np
import zarr
import os
import shutil
import sys

# Allow import of nas_monitor_client from repo root when run as:
#   uv run python examples/zarr_demo.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nas_monitor_client import NASMonitorClient

# Configuration
ZARR_PATH = "demo_write.zarr"
NUM_CHUNKS = 30
CHUNK_SIZE = (1000, 128, 128)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("ZarrDemo")

client = NASMonitorClient(host="localhost", port=7003, device="smlnas")
monitoring_active = True

def monitor_worker():
    global monitoring_active
    logger.info("Starting background monitoring thread...")
    while monitoring_active:
        summary = client.get_summary()
        if summary and "smlnas" in summary:
            s = summary["smlnas"]
            logger.info(f"[MONITOR] {s['name']} | Write: {s['write_mb_s']:.2f} MB/s | Read: {s['read_mb_s']:.2f} MB/s | Load: {s['peak_load']}%")
        time.sleep(2)

def perform_zarr_write():
    if os.path.exists(ZARR_PATH):
        shutil.rmtree(ZARR_PATH)
        
    client.mark_event("START_ZARR_WRITE")

    logger.info(f"Initializing Zarr array at {ZARR_PATH}...")
    z = zarr.open(
        ZARR_PATH,
        mode='w',
        shape=(NUM_CHUNKS * CHUNK_SIZE[0], CHUNK_SIZE[1], CHUNK_SIZE[2]),
        chunks=CHUNK_SIZE,
        dtype='f4'
    )

    logger.info(f"Writing {NUM_CHUNKS} chunks...")
    for i in range(NUM_CHUNKS):
        start_idx = i * CHUNK_SIZE[0]
        data = np.random.rand(*CHUNK_SIZE).astype(np.float32)
        t = time.perf_counter()
        z[start_idx:start_idx + CHUNK_SIZE[0]] = data
        if (i + 1) % 5 == 0:
            logger.info(f"[WRITE] Chunk {i+1}/{NUM_CHUNKS} in {time.perf_counter()-t:.2f}s")
        time.sleep(0.5)

    client.mark_event("END_ZARR_WRITE")

if __name__ == "__main__":
    mon_thread = threading.Thread(target=monitor_worker, daemon=True)
    mon_thread.start()

    try:
        t0 = time.perf_counter()
        perform_zarr_write()
        logger.info(f"Total write time: {time.perf_counter() - t0:.2f}s")
    finally:
        monitoring_active = False
        time.sleep(2)
        logger.info("Done.")
