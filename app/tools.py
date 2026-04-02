from __future__ import annotations

import shlex
import subprocess
from typing import Callable

import psutil

from app.config import settings
from app.models import RiskLevel, ToolResult
from app.monitoring import get_basic_metrics


APP_ALIASES: dict[str, tuple[str, ...]] = {
    "browser": ("firefox", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"),
    "chrome": ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"),
    "google chrome": ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"),
    "chromium": ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"),
    "firefox": ("firefox",),
    "file manager": ("nautilus", "dolphin", "thunar", "pcmanfm"),
    "terminal": ("gnome-terminal", "konsole", "xfce4-terminal", "xterm"),
    "files": ("nautilus", "dolphin", "thunar", "pcmanfm"),
    "settings": ("gnome-control-center", "systemsettings", "xfce4-settings-manager"),
}


def _run_command(cmd: list[str], timeout: int | None = None) -> ToolResult:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout or settings.tool_timeout_seconds,
            check=False,
        )
        ok = proc.returncode == 0
        summary = "Command succeeded." if ok else "Command failed."
        return ToolResult(
            ok=ok,
            summary=summary,
            data={
                "returncode": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "cmd": cmd,
            },
        )
    except subprocess.TimeoutExpired:
        return ToolResult(ok=False, summary="Command timed out.", data={"cmd": cmd})
    except Exception as exc:
        return ToolResult(ok=False, summary=f"Command error: {exc}", data={"cmd": cmd})


def tool_metrics() -> tuple[RiskLevel, Callable[[], ToolResult]]:
    def _exec() -> ToolResult:
        data = get_basic_metrics()
        return ToolResult(ok=True, summary="Current system metrics.", data=data)

    return RiskLevel.low, _exec


def tool_list_processes(limit: int = 20) -> tuple[RiskLevel, Callable[[], ToolResult]]:
    def _exec() -> ToolResult:
        plist = []
        for p in psutil.process_iter(attrs=["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                info = p.info
                if info.get("cpu_percent") is None:
                    info["cpu_percent"] = p.cpu_percent(interval=None)
                plist.append(info)
            except Exception:
                continue
        plist.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
        return ToolResult(ok=True, summary="Top processes.", data={"processes": plist[:limit]})

    return RiskLevel.medium, _exec


def tool_kill_process(pid: int) -> tuple[RiskLevel, Callable[[], ToolResult]]:
    def _exec() -> ToolResult:
        try:
            p = psutil.Process(pid)
            p.terminate()
            gone, alive = psutil.wait_procs([p], timeout=2)
            if alive:
                for proc in alive:
                    proc.kill()
            return ToolResult(ok=True, summary=f"Process {pid} terminated.")
        except psutil.NoSuchProcess:
            return ToolResult(ok=False, summary="No such process.")
        except psutil.AccessDenied:
            return ToolResult(ok=False, summary="Access denied.")
        except Exception as exc:
            return ToolResult(ok=False, summary=f"Kill failed: {exc}")

    return RiskLevel.high, _exec


def tool_system_control(action: str) -> tuple[RiskLevel, Callable[[], ToolResult]]:
    action = action.lower().strip()
    if action == "shutdown":
        cmd = ["shutdown", "now"]
    elif action == "restart":
        cmd = ["reboot"]
    elif action == "sleep":
        cmd = ["systemctl", "suspend"]
    elif action == "lock":
        cmd = ["loginctl", "lock-session"]
    else:
        def _bad() -> ToolResult:
            return ToolResult(ok=False, summary="Unsupported system action.", data={"action": action})

        return RiskLevel.medium, _bad

    return RiskLevel.high, lambda: _run_command(cmd)


def tool_shell(command_text: str) -> tuple[RiskLevel, Callable[[], ToolResult]]:
    tokens = shlex.split(command_text)
    if not tokens:
        return RiskLevel.low, lambda: ToolResult(ok=False, summary="No command provided.")

    executable = tokens[0]
    if executable not in settings.allowed_commands:
        return RiskLevel.medium, lambda: ToolResult(
            ok=False,
            summary=f"'{executable}' is blocked. Use one of the approved local commands instead.",
            data={"allowed": list(settings.allowed_commands), "requested": executable},
        )

    risk = RiskLevel.low if executable in {"ls", "pwd", "whoami", "date", "uptime"} else RiskLevel.medium
    return risk, lambda: _run_command(tokens)


def tool_open_app(app_name: str) -> tuple[RiskLevel, Callable[[], ToolResult]]:
    app = app_name.strip()

    def _exec() -> ToolResult:
        if not app:
            return ToolResult(ok=False, summary="App name is empty.")
        candidates = _candidate_apps(app)
        try:
            for candidate in candidates:
                try:
                    subprocess.Popen([candidate], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return ToolResult(ok=True, summary=f"Opened {candidate}.")
                except FileNotFoundError:
                    continue
            return ToolResult(ok=False, summary=f"Application not found: {app}")
        except Exception as exc:
            return ToolResult(ok=False, summary=f"Open app failed: {exc}")

    return RiskLevel.medium, _exec


def _candidate_apps(app_name: str) -> tuple[str, ...]:
    normalized = " ".join(app_name.lower().split())
    if normalized in APP_ALIASES:
        return APP_ALIASES[normalized]
    return (app_name.strip(),)
