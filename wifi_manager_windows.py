"""
wifi_manager_windows.py

Windows Wi-Fi backend using netsh.

Notes:
    - Scanning uses: netsh wlan show networks mode=bssid
    - Connecting to secured Wi-Fi creates a temporary XML Wi-Fi profile.
    - Enabling/disabling the adapter uses PowerShell Get-NetAdapter/Enable-NetAdapter.
      This may require running Python as Administrator depending on Windows policy.
"""

from __future__ import annotations

import html
import os
import re
import subprocess
import tempfile
from typing import List, Optional, Tuple

from wifi_manager import BaseWifiManager, CommandResult, WifiNetwork


class WindowsNetshWifiManager(BaseWifiManager):
    def _run(self, command: List[str], timeout: int = 30) -> CommandResult:
        try:
            result = subprocess.run(
                command,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout,
                shell=False,
            )
            return CommandResult(
                ok=result.returncode == 0,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
            )
        except Exception as exc:
            return CommandResult(ok=False, stderr=str(exc))

    def _run_powershell(self, script: str, timeout: int = 30) -> CommandResult:
        return self._run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            timeout=timeout,
        )

    def get_adapter_name(self) -> Optional[str]:
        script = (
            "Get-NetAdapter | "
            "Where-Object { $_.NdisPhysicalMedium -eq 9 -or $_.InterfaceDescription -match 'Wireless|Wi-Fi|802.11' } | "
            "Select-Object -First 1 -ExpandProperty Name"
        )
        result = self._run_powershell(script)
        if result.ok and result.stdout.strip():
            return result.stdout.strip().splitlines()[0].strip()
        return None

    def get_status(self) -> CommandResult:
        adapter = self.get_adapter_name()
        if not adapter:
            return CommandResult(ok=False, stderr="No Windows Wi-Fi adapter found")

        script = f"(Get-NetAdapter -Name {adapter!r}).Status"
        result = self._run_powershell(script)
        if result.ok:
            result.stdout = f"Wi-Fi adapter '{adapter}' is {result.stdout.strip()}"
        return result


    def is_wifi_enabled(self) -> bool:
        adapter = self.get_adapter_name()
        if not adapter:
            return False

        script = f"(Get-NetAdapter -Name {adapter!r}).Status"
        result = self._run_powershell(script)

        if not result.ok:
            return False

        status = result.stdout.strip().lower()

        print(f"WiFi Status = '{status}'")

        return status == "up"



    def enable_wifi(self) -> CommandResult:
        adapter = self.get_adapter_name()
        if not adapter:
            return CommandResult(ok=False, stderr="No Windows Wi-Fi adapter found")

        script = f"""
        Enable-NetAdapter -Name {adapter!r} -Confirm:$false -ErrorAction SilentlyContinue
        netsh interface set interface name={adapter!r} admin=enabled
        """

        return self._run_powershell(script)
    
    # def enable_wifi(self) -> CommandResult:
    #     adapter = self.get_adapter_name()
    #     if not adapter:
    #         return CommandResult(ok=False, stderr="No Windows Wi-Fi adapter found")

    #     script = f"Enable-NetAdapter -Name {adapter!r} -Confirm:$false"
    #     return self._run_powershell(script)

    def disable_wifi(self) -> CommandResult:
        adapter = self.get_adapter_name()
        if not adapter:
            return CommandResult(ok=False, stderr="No Windows Wi-Fi adapter found")

        script = f"Disable-NetAdapter -Name {adapter!r} -Confirm:$false"
        return self._run_powershell(script)

    def scan_networks(self) -> Tuple[CommandResult, List[WifiNetwork]]:
        self.enable_wifi()

        result = self._run(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            timeout=30
        )

        print("========================================")
        print(result.stdout)
        print("========================================")


        if not result.ok:
            return result, []

        networks: List[WifiNetwork] = []

        current_ssid = ""
        current_security = ""
        best_signal = 0
        seen = set()

        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()

            ssid_match = re.match(r"^SSID\s+\d+\s*:\s*(.*)$", line, re.IGNORECASE)
            if ssid_match:
                if current_ssid:
                    key = current_ssid.lower()
                    if key not in seen:
                        networks.append(
                            WifiNetwork(
                                ssid=current_ssid,
                                signal=str(best_signal),
                                security=current_security,
                            )
                        )
                        seen.add(key)

                current_ssid = ssid_match.group(1).strip()
                current_security = ""
                best_signal = 0
                continue

            auth_match = re.match(r"^Authentication\s*:\s*(.*)$", line, re.IGNORECASE)
            if auth_match:
                current_security = auth_match.group(1).strip()
                continue

            signal_match = re.match(r"^Signal\s*:\s*(\d+)%", line, re.IGNORECASE)
            if signal_match:
                signal_value = int(signal_match.group(1))
                best_signal = max(best_signal, signal_value)
                continue

        if current_ssid:
            key = current_ssid.lower()
            if key not in seen:
                networks.append(
                    WifiNetwork(
                        ssid=current_ssid,
                        signal=str(best_signal),
                        security=current_security,
                    )
                )

        networks.sort(key=lambda n: int(n.signal or 0), reverse=True)

        return CommandResult(
            ok=True,
            stdout=f"Found {len(networks)} network(s)"
        ), networks



    def is_connected_to(self, ssid: str) -> bool:
        result = self._run(
            ["netsh", "wlan", "show", "interfaces"],
            timeout=10,
        )

        if not result.ok:
            return False

        current_ssid = None
        state = None

        for line in result.stdout.splitlines():
            line = line.strip()

            if line.startswith("State"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    state = parts[1].strip().lower()

            elif re.match(r"^SSID\s*:", line):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    current_ssid = parts[1].strip()

        return (
            state == "connected"
            and current_ssid is not None
            and current_ssid.lower() == ssid.lower()
        )


    def connect(self, ssid: str, password: str = "") -> CommandResult:
        ssid = ssid.strip()
        password = password.strip()

        if not ssid:
            return CommandResult(ok=False, stderr="SSID is required")

        self.enable_wifi()

        profile_xml = self._build_wifi_profile_xml(ssid, password)

        fd, profile_path = tempfile.mkstemp(prefix="wifi_profile_", suffix=".xml")
        os.close(fd)

        try:
            with open(profile_path, "w", encoding="utf-8") as f:
                f.write(profile_xml)

            add_result = self._run(["netsh", "wlan", "add", "profile", f"filename={profile_path}"])
            if not add_result.ok:
                return add_result

            connect_result = self._run(["netsh", "wlan", "connect", f"name={ssid}"], timeout=45)
            if connect_result.ok:
                connect_result.stdout = f"Connect request sent for {ssid}"
            return connect_result

        finally:
            try:
                os.remove(profile_path)
            except OSError:
                pass

    def _build_wifi_profile_xml(self, ssid: str, password: str) -> str:
        escaped_ssid = html.escape(ssid, quote=True)
        escaped_password = html.escape(password, quote=True)

        if password:
            return f'''<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{escaped_ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{escaped_ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{escaped_password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>
'''

        return f'''<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{escaped_ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{escaped_ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>open</authentication>
                <encryption>none</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
        </security>
    </MSM>
</WLANProfile>
'''
