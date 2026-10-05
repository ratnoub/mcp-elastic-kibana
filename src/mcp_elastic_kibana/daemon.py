"""Mekanisme daemon: jalankan MCP server di background.

File daemon disimpan di ~/.config/mcp-elastic-kibana/:
  - daemon.pid  (PID proses background)
  - daemon.log  (output server)
"""

import ctypes
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

DAEMON_DIR = Path.home() / ".config" / "mcp-elastic-kibana"
PID_FILE = DAEMON_DIR / "daemon.pid"
LOG_FILE = DAEMON_DIR / "daemon.log"


def _is_windows() -> bool:
    return os.name == "nt"


def _pid_alive(pid: int) -> bool:
    """Cek apakah proses dengan PID masih berjalan (cross-platform)."""
    if _is_windows():
        # Catatan: os.kill(pid, 0) di Windows justru memanggil TerminateProcess,
        # jadi gunakan OpenProcess via ctypes.
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return kernel32.GetLastError() == 5  # ERROR_ACCESS_DENIED -> masih ada
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_pid() -> Optional[int]:
    """Baca PID daemon yang masih hidup, atau None."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if _pid_alive(pid):
                return pid
        except ValueError:
            pass
    return None


def port_open(port: int) -> bool:
    """Cek apakah port sudah menerima koneksi (server aktif)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_daemon(host: str, port: int, config_path: Optional[str] = None) -> int:
    """Jalankan server sebagai proses background terdetach. Kembalikan PID."""
    existing = read_pid()
    if existing is not None:
        raise RuntimeError(f"Daemon sudah berjalan (PID {existing}). "
                           f"Jalankan 'mcp-elastic-kibana --stop' dulu.")

    DAEMON_DIR.mkdir(parents=True, exist_ok=True)
    log = open(LOG_FILE, "ab")
    cmd = [
        sys.executable,
        "-m",
        "mcp_elastic_kibana.cli",
        "--transport", "http",
        "--host", host,
        "--port", str(port),
    ]
    if config_path:
        cmd += ["--config", config_path]
    kwargs: dict = dict(
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
            cwd=os.getcwd(),
    )
    if _is_windows():
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **kwargs)
    PID_FILE.write_text(str(proc.pid))
    return proc.pid


def stop_daemon() -> None:
    """Hentikan daemon background (SIGTERM, lalu SIGKILL jika perlu)."""
    pid = read_pid()
    if pid is None:
        raise RuntimeError("Daemon tidak berjalan (PID file tidak valid).")

    os.kill(pid, signal.SIGTERM)
    for _ in range(20):
        if not _pid_alive(pid):
            break
        time.sleep(0.25)
    if _pid_alive(pid):
        os.kill(pid, signal.SIGKILL)
    PID_FILE.unlink(missing_ok=True)


def status(host: str, port: int) -> dict:
    """Status daemon: PID, port, dan lokasi log."""
    pid = read_pid()
    return {
        "running": pid is not None,
        "pid": pid,
        "port_open": port_open(port),
        "url": f"http://{host}:{port}/mcp" if host != "0.0.0.0" else f"http://<ip-server>:{port}/mcp",
        "log_file": str(LOG_FILE),
    }