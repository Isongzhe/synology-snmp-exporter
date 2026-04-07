import requests
import time
import logging

class NASMonitorClient:
    """
    A simple, portable client for the NAS SNMP Monitoring API.
    Copy this class into your benchmark scripts for easy event marking and metrics retrieval.
    """
    def __init__(self, host="localhost", port=7003, device="smlnas"):
        self.base_url = f"http://{host}:{port}"
        self.device = device
        self.logger = logging.getLogger("NASMonitorClient")

    def mark_event(self, event_name: str):
        """Send a marker event to the monitor's history log."""
        url = f"{self.base_url}/metrics/{self.device}/event"
        try:
            resp = requests.post(url, json={"name": event_name}, timeout=2)
            if resp.status_code == 200:
                self.logger.debug(f"Event '{event_name}' recorded.")
                return True
        except Exception as e:
            self.logger.warning(f"Failed to send event '{event_name}': {e}")
        return False

    def get_realtime_metrics(self):
        """Fetch the latest raw metrics for the configured device."""
        url = f"{self.base_url}/metrics/{self.device}"
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            self.logger.warning(f"Failed to fetch real-time metrics: {e}")
        return None

    def get_avg_metrics(self):
        """Fetch the 1-minute averaged metrics for the configured device."""
        url = f"{self.base_url}/metrics/{self.device}/avg/1m"
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            self.logger.warning(f"Failed to fetch averaged metrics: {e}")
        return None

    def get_summary(self):
        """Get a summary of all monitored NAS devices."""
        url = f"{self.base_url}/summary"
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            self.logger.warning(f"Failed to fetch summary: {e}")
        return None
