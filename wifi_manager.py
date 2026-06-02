"""
wifi_manager.py

Cross-platform Wi-Fi manager factory.

The CustomTkinter UI should use this module instead of calling nmcli/netsh
itself. This keeps the UI code portable between Raspberry Pi OS/Linux and
Windows.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class WifiNetwork:
    ssid: str
    signal: str = ""
    security: str = ""


@dataclass
class CommandResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""

    @property
    def message(self) -> str:
        if self.ok:
            return self.stdout.strip()
        return self.stderr.strip() or self.stdout.strip()


class BaseWifiManager:
    """Base interface used by WifiSettingsPage."""

    def get_status(self) -> CommandResult:
        raise NotImplementedError

    def enable_wifi(self) -> CommandResult:
        raise NotImplementedError

    def disable_wifi(self) -> CommandResult:
        raise NotImplementedError

    def scan_networks(self) -> Tuple[CommandResult, List[WifiNetwork]]:
        raise NotImplementedError

    def connect(self, ssid: str, password: str = "") -> CommandResult:
        raise NotImplementedError

    def get_adapter_name(self) -> Optional[str]:
        return None


def get_wifi_manager() -> BaseWifiManager:
    """Return the correct Wi-Fi manager for the current OS."""

    system = platform.system().lower()

    if system == "windows":
        from wifi_manager_windows import WindowsNetshWifiManager

        return WindowsNetshWifiManager()

    if system == "linux":
        from wifi_manager_linux import LinuxNmcliWifiManager

        return LinuxNmcliWifiManager()

    raise RuntimeError(f"Unsupported OS for Wi-Fi manager: {platform.system()}")
