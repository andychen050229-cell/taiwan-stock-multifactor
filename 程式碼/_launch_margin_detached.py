"""
Truly-detached launcher for 抓取融資融券.py.

Uses subprocess.Popen with CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS so the
child python process becomes independent of the parent shell/terminal. That
way Claude Code's bash-tool exit (or any harness cleanup) cannot kill it.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

log_path = ROOT / "outputs" / "logs" / "margin_fetch.log"
log_path.parent.mkdir(parents=True, exist_ok=True)

# Append mode so we preserve the earlier run history
log_fp = open(log_path, "ab", buffering=0)

script = ROOT / "程式碼" / "資料抓取" / "抓取融資融券.py"

# Windows: CREATE_NEW_PROCESS_GROUP (0x200) | DETACHED_PROCESS (0x8)
# Popen close_fds=True ensures no inherited handles; stdin is DEVNULL
creation_flags = 0
if sys.platform == "win32":
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008  # DETACHED_PROCESS

proc = subprocess.Popen(
    [sys.executable, str(script)],
    stdout=log_fp,
    stderr=log_fp,
    stdin=subprocess.DEVNULL,
    env=env,
    cwd=str(ROOT),
    close_fds=True,
    creationflags=creation_flags,
)

print(f"Launched detached margin fetch: PID={proc.pid}")
print(f"Log: {log_path}")

# Save PID for later monitoring
pid_file = ROOT / "outputs" / "logs" / "margin_fetch.pid"
pid_file.write_text(str(proc.pid), encoding="utf-8")
print(f"PID file: {pid_file}")
