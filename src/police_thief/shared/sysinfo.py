"""Machine specification for the Step-0 computational-fairness declaration.

Before the first move each agent declares its hardware - operating system, CPU
cores and frequency, memory, graphics accelerator - alongside its language
model, code version, team name and mini-game number. The league's normalization
rewards algorithmic efficiency over raw compute, so the declaration must be
honest and is cryptographically sealed (rulebook ch. 5.5).

**Honest means measured.** The first version read ``/proc/cpuinfo`` and
``os.sysconf`` and nothing else, so on the Windows laptop this team actually
plays on it declared ``cpu_mhz: 0.0, ram_gb: 0.0`` - a machine with no clock and
no memory. Rule #24's sanction for a bad hardware declaration is loss of the
computational-fairness bonus, and the bonus rewards doing more with less: a
declaration of zero throws away the very evidence it exists to provide. Each
probe now tries the platforms in turn and falls back to 0.0 only when the host
genuinely will not say.
"""

from __future__ import annotations

import ctypes
import os
import platform
import subprocess
from typing import Any


class _MemoryStatusEx(ctypes.Structure):
    """Windows ``MEMORYSTATUSEX``, for ``GlobalMemoryStatusEx``."""

    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _windows_ram_bytes() -> int:
    """Total physical memory via ``GlobalMemoryStatusEx``, or 0."""
    try:
        status = _MemoryStatusEx()
        status.dwLength = ctypes.sizeof(_MemoryStatusEx)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys)
    except (AttributeError, OSError):  # pragma: no cover - non-Windows
        pass
    return 0


def _windows_cpu_mhz() -> float:
    """Nominal CPU frequency from the registry, or 0.0.

    The registry value is the *nominal* clock, which is the honest figure for a
    fairness declaration: a turbo reading sampled mid-match would vary with
    thermal state and describe the moment rather than the machine.
    """
    try:
        import winreg  # noqa: PLC0415 - Windows-only, imported where used

        key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            return float(winreg.QueryValueEx(key, "~MHz")[0])
    except (ImportError, OSError, ValueError):  # pragma: no cover - non-Windows
        return 0.0


def _sysctl(name: str) -> str:
    """One ``sysctl -n`` value on macOS/BSD, or an empty string."""
    try:
        result = subprocess.run(
            ["sysctl", "-n", name], capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        return ""


def _cpu_frequency_mhz() -> float:
    """Best-effort CPU frequency; zero only when the platform truly hides it."""
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as handle:
            for line in handle:
                if line.lower().startswith("cpu mhz"):
                    return round(float(line.split(":")[1]), 1)
    except (OSError, ValueError, IndexError):
        pass
    if (windows := _windows_cpu_mhz()) > 0:
        return round(windows, 1)
    if hz := _sysctl("hw.cpufrequency"):
        try:
            return round(float(hz) / 1_000_000, 1)
        except ValueError:  # pragma: no cover
            pass
    return 0.0


def _total_ram_gb() -> float:
    """Total physical memory in gigabytes, zero when undetectable."""
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * page_size / (1024**3), 2)
    except (ValueError, OSError, AttributeError):
        pass
    if (windows := _windows_ram_bytes()) > 0:
        return round(windows / (1024**3), 2)
    if raw := _sysctl("hw.memsize"):
        try:
            return round(float(raw) / (1024**3), 2)
        except ValueError:  # pragma: no cover
            pass
    return 0.0


def _gpu_description() -> str:
    """A best-effort GPU description; honest 'none detected' otherwise.

    League play runs on plain laptops; a missing accelerator is the common
    case and reporting it plainly is exactly what fairness wants.
    """
    for path in ("/proc/driver/nvidia/version",):
        try:
            with open(path, encoding="utf-8") as handle:
                return handle.readline().strip()[:80]
        except OSError:
            continue
    return "none detected"


def hardware_spec() -> dict[str, Any]:
    """The machine specification the Step-0 declaration seals."""
    return {
        "os": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu_cores": os.cpu_count() or 0,
        "cpu_mhz": _cpu_frequency_mhz(),
        "ram_gb": _total_ram_gb(),
        "gpu": _gpu_description(),
    }
