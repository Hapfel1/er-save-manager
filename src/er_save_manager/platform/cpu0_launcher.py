"""
Launch eldenring.exe or ersc_launcher.exe with CPU 0 excluded from the process affinity mask.

Windows only. The affinity is applied after the process appears in the process list.
All operations use ctypes so no external dependencies are required.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import subprocess
import sys
import time
from pathlib import Path

# Win32 constants
_PROCESS_QUERY_INFORMATION = 0x0400
_PROCESS_SET_INFORMATION = 0x0200

_kernel32 = (
    ctypes.WinDLL("kernel32", use_last_error=True) if sys.platform == "win32" else None
)


def _cpu_count() -> int:
    """Return the logical processor count reported by Windows."""
    if _kernel32 is None:
        return 1
    si = ctypes.wintypes.SYSTEM_INFO()
    _kernel32.GetSystemInfo(ctypes.byref(si))
    return si.dwNumberOfProcessors


def _full_affinity_mask() -> int:
    """Bitmask with one bit set per logical processor."""
    return (1 << _cpu_count()) - 1


def _affinity_without_cpu0() -> int:
    """Full affinity mask with bit 0 cleared."""
    return _full_affinity_mask() & ~1


def _set_affinity(pid: int, mask: int) -> bool:
    """Apply mask to the process identified by pid. Returns True on success."""
    if _kernel32 is None:
        return False
    handle = _kernel32.OpenProcess(
        _PROCESS_QUERY_INFORMATION | _PROCESS_SET_INFORMATION, False, pid
    )
    if not handle:
        return False
    try:
        return bool(_kernel32.SetProcessAffinityMask(handle, ctypes.c_size_t(mask)))
    finally:
        _kernel32.CloseHandle(handle)


def _get_pid_by_name_csv(name: str) -> int | None:
    """
    Return the PID of the first process matching name via tasklist CSV output.

    Uses STARTUPINFO + CREATE_NO_WINDOW to suppress any console window.
    """
    if sys.platform != "win32":
        return None
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            startupinfo=si,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=3,
        )
    except Exception:
        return None
    for line in result.stdout.decode(errors="replace").splitlines():
        parts = [p.strip('"') for p in line.split(",")]
        if len(parts) >= 2 and parts[0].lower() == name.lower():
            try:
                return int(parts[1])
            except ValueError:
                continue
    return None


def apply_cpu0_exclusion(process_name: str) -> bool:
    """
    Find a running process by name and remove CPU 0 from its affinity mask.

    Intended to be called from the process monitor on a launch transition.
    Returns True if the affinity was successfully updated.
    """
    if sys.platform != "win32":
        return False
    if _cpu_count() <= 1:
        return False
    pid = _get_pid_by_name_csv(process_name)
    if pid is None:
        return False
    return _set_affinity(pid, _affinity_without_cpu0())


class LaunchResult:
    """Outcome of a launch attempt."""

    __slots__ = ("success", "message")

    def __init__(self, success: bool, message: str) -> None:
        self.success = success
        self.message = message


def launch_with_cpu0_excluded(
    exe_path: Path,
    *,
    poll_interval: float = 0.25,
    timeout: float = 30.0,
) -> LaunchResult:
    """
    Launch exe_path and remove CPU 0 from its affinity mask once it appears.

    Parameters
    ----------
    exe_path:
        Path to eldenring.exe or ersc_launcher.exe.
    poll_interval:
        Seconds between PID-lookup attempts after launch.
    timeout:
        Maximum seconds to wait for the process to appear before giving up.

    Returns
    -------
    LaunchResult with success flag and a human-readable message.
    """
    if sys.platform != "win32":
        return LaunchResult(False, "CPU affinity control is only available on Windows.")

    if not exe_path.is_file():
        return LaunchResult(False, f"Executable not found: {exe_path}")

    cpu_count = _cpu_count()
    if cpu_count <= 1:
        return LaunchResult(
            False, "Only one logical processor detected; cannot exclude CPU 0."
        )

    process_name = exe_path.name.lower()
    mask = _affinity_without_cpu0()

    # Launch the process detached so it outlives the tool.
    try:
        subprocess.Popen(
            [str(exe_path)],
            cwd=str(exe_path.parent),
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            close_fds=True,
        )
    except OSError as exc:
        return LaunchResult(False, f"Failed to launch: {exc}")

    # Poll until the process appears in the process list.
    deadline = time.monotonic() + timeout
    pid: int | None = None
    while time.monotonic() < deadline:
        pid = _get_pid_by_name_csv(process_name)
        if pid is not None:
            break
        time.sleep(poll_interval)

    if pid is None:
        return LaunchResult(
            False,
            f"Process '{process_name}' did not appear within {timeout:.0f}s after launch.",
        )

    if not _set_affinity(pid, mask):
        err = ctypes.get_last_error()
        return LaunchResult(
            False, f"SetProcessAffinityMask failed (Win32 error {err})."
        )

    excluded_cores = 1
    active_cores = cpu_count - excluded_cores
    return LaunchResult(
        True,
        f"Launched '{process_name}' (PID {pid}) with CPU 0 excluded "
        f"({active_cores}/{cpu_count} cores active).",
    )
