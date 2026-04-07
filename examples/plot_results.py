import pandas as pd
import json
import matplotlib.pyplot as plt
import os
import sys
from datetime import datetime

# Allow running from repo root: uv run python examples/plot_results.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOG_FILE = "nas_metrics_history_raw.jsonl"
OUTPUT_PLOT = "nas_benchmark_result.png"

def parse_logs(file_path):
    data = []
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return None
    with open(file_path, "r") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except Exception:
                continue
    return data

def plot_results():
    raw_data = parse_logs(LOG_FILE)
    if not raw_data:
        return

    rows, markers = [], []
    for entry in raw_data:
        if "event" in entry:
            markers.append({
                "time": datetime.fromtimestamp(entry['wall_time']),
                "label": entry['event']
            })
            continue
        ios = entry.get('storage_io', [])
        rows.append({
            "timestamp": datetime.fromtimestamp(entry['wall_time']),
            "write_mb_s": sum(io['write_mb_s'] for io in ios),
            "read_mb_s": sum(io['read_mb_s'] for io in ios),
            "w_iops": sum(io['w_iops'] for io in ios),
            "r_iops": sum(io['r_iops'] for io in ios),
            "peak_load": max(io['load_pct'] for io in ios) if ios else 0
        })

    df = pd.DataFrame(rows)
    if df.empty:
        print("No data to plot.")
        return
    df.set_index("timestamp", inplace=True)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    # Draw event markers
    for m in markers:
        color = "red" if "START" in m["label"] else "black"
        ax1.axvline(m["time"], color=color, linestyle="--", alpha=0.6)
        ax2.axvline(m["time"], color=color, linestyle="--", alpha=0.6)
        ax1.text(m["time"], ax1.get_ylim()[1] * 0.9, m["label"],
                 color=color, rotation=90, va='top', fontsize=8)

    # Throughput
    ax1.plot(df.index, df.write_mb_s, label="Write (MB/s)", color="tab:blue", linewidth=2)
    ax1.plot(df.index, df.read_mb_s, label="Read (MB/s)", color="tab:green", linestyle="--")
    ax1.set_ylabel("Throughput (MB/s)")
    ax1.set_title("NAS Storage Benchmark")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # IOPs + Load
    ax2.plot(df.index, df.w_iops, label="Write IOPs", color="tab:orange")
    ax2.plot(df.index, df.r_iops, label="Read IOPs", color="tab:red", linestyle=":")
    ax2.set_ylabel("IOPs")
    ax3 = ax2.twinx()
    ax3.fill_between(df.index, 0, df.peak_load, color="gray", alpha=0.1, label="Disk Load %")
    ax3.set_ylim(0, 105)
    ax3.set_ylabel("Load (%)")
    lines, labels = ax2.get_legend_handles_labels()
    lines2, labels2 = ax3.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc="upper left")
    ax2.set_xlabel("Time")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_PLOT)
    print(f"Plot saved to {OUTPUT_PLOT}")

if __name__ == "__main__":
    plot_results()
