"""Local system health metrics (offline, using psutil)."""
from __future__ import annotations

import shutil

import psutil

from .base import NO_PARAMS, Tool, ok


def _bytes_to_gb(n: int) -> float:
    return round(n / (1024 ** 3), 2)


def get_system_health() -> dict:
    """Return CPU, memory, disk and battery usage for the local machine."""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    vm = psutil.virtual_memory()
    du = shutil.disk_usage("/")

    info: dict = {
        "cpu": {
            "usage_percent": cpu_percent,
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_logical": psutil.cpu_count(logical=True),
        },
        "memory": {
            "total_gb": _bytes_to_gb(vm.total),
            "used_gb": _bytes_to_gb(vm.used),
            "available_gb": _bytes_to_gb(vm.available),
            "usage_percent": vm.percent,
        },
        "disk": {
            "total_gb": _bytes_to_gb(du.total),
            "used_gb": _bytes_to_gb(du.used),
            "free_gb": _bytes_to_gb(du.free),
            "usage_percent": round(du.used / du.total * 100, 1) if du.total else 0,
        },
    }

    # Battery is not present on servers / desktops without one.
    try:
        battery = psutil.sensors_battery()
        if battery is not None:
            info["battery"] = {
                "percent": battery.percent,
                "plugged_in": battery.power_plugged,
            }
    except Exception:
        pass

    return ok(info)


def get_tools() -> list[Tool]:
    return [
        Tool(
            name="get_system_health",
            description="Get local machine health: CPU usage, RAM usage, disk "
                        "usage and battery status.",
            category="System",
            parameters=NO_PARAMS,
            func=get_system_health,
        )
    ]
