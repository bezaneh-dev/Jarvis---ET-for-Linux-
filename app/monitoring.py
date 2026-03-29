from __future__ import annotations

import glob
import time
from typing import Any

import psutil

_last_net = None
_last_time = None


def _get_net_delta() -> dict[str, float]:
    global _last_net, _last_time
    now = time.time()
    counters = psutil.net_io_counters()
    if _last_net is None:
        _last_net = counters
        _last_time = now
        return {"bytes_sent_per_s": 0.0, "bytes_recv_per_s": 0.0}

    dt = max(now - (_last_time or now), 1e-6)
    sent_rate = (counters.bytes_sent - _last_net.bytes_sent) / dt
    recv_rate = (counters.bytes_recv - _last_net.bytes_recv) / dt

    _last_net = counters
    _last_time = now
    return {"bytes_sent_per_s": sent_rate, "bytes_recv_per_s": recv_rate}


def _read_temp_fallback() -> float | None:
    temps: list[float] = []
    for path in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                milli = int(f.read().strip())
                temps.append(milli / 1000.0)
        except Exception:
            continue
    if not temps:
        return None
    return sum(temps) / len(temps)


def get_basic_metrics() -> dict[str, Any]:
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()

    try:
        disk = psutil.disk_usage("/")
    except Exception:
        disk = None

    temp = None
    try:
        tdata = psutil.sensors_temperatures()
        if tdata:
            for _, entries in tdata.items():
                if entries:
                    temp = entries[0].current
                    break
    except Exception:
        temp = None

    if temp is None:
        temp = _read_temp_fallback()

    return {
        "cpu_percent": cpu,
        "cpu_temp": temp,
        "memory_percent": mem.percent,
        "memory_used_gb": round(mem.used / (1024**3), 2),
        "memory_total_gb": round(mem.total / (1024**3), 2),
        "disk_percent": 0 if disk is None else disk.percent,
        "disk_used_gb": 0 if disk is None else round(disk.used / (1024**3), 2),
        "disk_total_gb": 0 if disk is None else round(disk.total / (1024**3), 2),
        "uptime_seconds": int(time.time() - psutil.boot_time()),
        **_get_net_delta(),
    }
