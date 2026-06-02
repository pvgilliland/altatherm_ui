"""
wifi_manager_linux.py

Linux/Raspberry Pi OS Wi-Fi backend using nmcli.

Requirements:
    sudo apt install network-manager

Important:
    This will not work if Wi-Fi is disabled in config.txt with:
        dtoverlay=disable-wifi

Use nmcli radio wifi off/on instead if you want runtime control.
"""

from __future__ import annotations

import subprocess
import time
from typing import List, Tuple

from wifi_manager import BaseWifiManager, CommandResult, WifiNetwork


class LinuxNmcliWifiManager(BaseWifiManager):
    def _run(self, command: List[str], timeout: int = 20) -> CommandResult:
        try:
            result = subprocess.run(
                command,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout,
            )
            return CommandResult(
                ok=result.returncode == 0,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
            )
        except Exception as exc:
            return CommandResult(ok=False, stderr=str(exc))

    def get_status(self) -> CommandResult:
        result = self._run(["nmcli", "radio", "wifi"])
        if result.ok:
            result.stdout = f"Wi-Fi radio is {result.stdout}"
        return result

    def enable_wifi(self) -> CommandResult:
        return self._run(["nmcli", "radio", "wifi", "on"])

    def disable_wifi(self) -> CommandResult:
        return self._run(["nmcli", "radio", "wifi", "off"])

    def scan_networks(self) -> Tuple[CommandResult, List[WifiNetwork]]:
        self.enable_wifi()

        # Rescan can return before the scan result list is fully refreshed.
        self._run(["nmcli", "device", "wifi", "rescan"], timeout=15)
        time.sleep(1.0)

        result = self._run(
            [
                "nmcli",
                "-t",
                "-f",
                "SSID,SIGNAL,SECURITY",
                "device",
                "wifi",
                "list",
            ],
            timeout=20,
        )

        if not result.ok:
            return result, []

        networks: List[WifiNetwork] = []
        seen = set()

        for line in result.stdout.splitlines():
            # nmcli -t uses ':' separators. SSIDs containing ':' are uncommon,
            # so this keeps the parser simple for HMI use.
            parts = line.split(":")
            if len(parts) < 3:
                continue

            ssid = parts[0].strip()
            signal = parts[1].strip()
            security = ":".join(parts[2:]).strip()

            if not ssid or ssid in seen:
                continue

            seen.add(ssid)
            networks.append(WifiNetwork(ssid=ssid, signal=signal, security=security))

        return CommandResult(ok=True, stdout=f"Found {len(networks)} network(s)"), networks

    def is_connected_to(self, ssid: str) -> bool:
        result = self._run(
            ["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi"],
            timeout=10,
        )

        if not result.ok:
            return False

        for line in result.stdout.splitlines():
            if line.startswith("yes:"):
                current_ssid = line[4:].strip()
                return current_ssid == ssid

        return False

    def connect(self, ssid: str, password: str = "") -> CommandResult:
        ssid = ssid.strip()
        password = password.strip()

        if not ssid:
            return CommandResult(ok=False, stderr="SSID is required")

        self.enable_wifi()

        if password:
            command = ["nmcli", "device", "wifi", "connect", ssid, "password", password]
        else:
            command = ["nmcli", "device", "wifi", "connect", ssid]

        result = self._run(command, timeout=45)

        if result.ok:
            result.stdout = f"Connected to {ssid}"

        return result
