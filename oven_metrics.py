"""Durable cooking-cycle uploads over the SIM7600 network interface."""

import json
from copy import deepcopy
from ipaddress import IPv4Address
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
from datetime import datetime, timezone
from threading import Event, Lock, Thread
from uuid import uuid4

logger = logging.getLogger(__name__)
CYCLES_URL = "https://metrics-altathermdhi.cloud/api/cooking-cycles"
JOBS_URL = "https://metrics-altathermdhi.cloud/api/oven-jobs"

# Set these locally for the oven running this copy of the HMI.
OVEN_SERIAL = "ALT-TEST-001"
OVEN_API_KEY = "2112xSHdCrXIvnXcLj1Z7GA_D8CCS2L8IzBgFeLZI98iyXI13580"
WINDOWS_CELLULAR_IPV4 = "10.172.6.51"
LINUX_CELLULAR_INTERFACE = ""


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _cellular_curl_options(interface):
    if os.name == "nt":
        return ["--ipv4", "--interface", str(IPv4Address(interface))]
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,15}", interface):
        raise ValueError("Expected a cellular network interface name")
    return ["--interface", "if!" + interface]


class CookingCycle:
    def __init__(self, uploader, recipe_name, *, mode, job_settings, job_file=None):
        self._uploader = uploader
        self._recipe_name = recipe_name
        self._job = {
            "mode": mode,
            "job_file": job_file,
            "job_settings": deepcopy(job_settings),
        }
        self._id = str(uuid4())
        self._started = _utc_now()
        self._lock = Lock()
        self._finished = False
        self._canceled = False

    def cancel(self):
        with self._lock:
            self._canceled = True

    def finish(self, result):
        with self._lock:
            if self._finished:
                return
            self._finished = True
            payload = {
                "cycle_uuid": self._id,
                "recipe_name": self._recipe_name[:100],
                "start_time": self._started,
                "end_time": max(self._started, _utc_now()),
                "result": "canceled" if self._canceled else result,
                **self._job,
            }
        self._uploader.enqueue(payload)


class OvenMetrics:
    @classmethod
    def from_settings(cls):
        serial = OVEN_SERIAL
        key = OVEN_API_KEY
        interface = (
            WINDOWS_CELLULAR_IPV4 if os.name == "nt" else LINUX_CELLULAR_INTERFACE
        )
        if not serial and not key:
            logger.info(
                "Oven uploads are disabled until an oven serial and API key are configured"
            )
            return None
        if not all(re.fullmatch(r"[!-~]+", value) for value in (serial, key)):
            logger.error("Metrics requires an oven serial and key")
            return None
        try:
            _cellular_curl_options(interface)
        except ValueError:
            logger.error(
                "Metrics requires the cellular IPv4 address on Windows or interface name on Linux"
            )
            return None
        if not shutil.which("curl"):
            logger.error("Metrics requires curl")
            return None
        state = Path(
            os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
        )
        try:
            spool = state / "altatherm" / "oven-metrics" / serial.encode().hex()
            return cls(serial, key, interface, spool)
        except (OSError, RuntimeError):
            logger.exception("Could not initialize the oven metrics queue")
            return None

    def __init__(self, serial, key, interface, spool):
        self._headers = (
            f"X-Oven-Serial: {serial}\nX-Oven-Key: {key}\n"
            "Content-Type: application/json\n"
        )
        self._interface_options = _cellular_curl_options(interface)
        self._spool = spool
        self._spool.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._wake = Event()
        Thread(target=self._run, name="oven-metrics", daemon=True).start()

    def begin(self, recipe_name, *, mode, job_settings, job_file=None):
        return CookingCycle(
            self, recipe_name, mode=mode, job_settings=job_settings, job_file=job_file
        )

    def begin_program(self, program_number, zone_sequences):
        settings = {
            "zones": {
                zone: [
                    {"duration_seconds": duration, "power_percent": int(power)}
                    for duration, power in steps
                ]
                for zone, steps in zone_sequences
            }
        }
        return self.begin(
            f"Program {program_number}",
            mode="AUTO",
            job_file=f"program{program_number}.alt",
            job_settings=settings,
        )

    def enqueue(self, payload):
        pending = self._spool / (payload["cycle_uuid"] + ".json")
        temporary = pending.with_suffix(".tmp")
        try:
            temporary.write_text(json.dumps(payload), encoding="utf-8")
            temporary.replace(pending)
        except OSError:
            logger.exception("Could not save cooking cycle %s", payload["cycle_uuid"])
            return
        self._wake.set()

    def _upload(self, pending):
        try:
            payload = json.loads(pending.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            logger.exception("Could not read queued cooking record %s", pending.name)
            return
        # Older records have no job settings and still belong to the cycle API.
        url = JOBS_URL if "job_settings" in payload else CYCLES_URL
        response = subprocess.run(
            [
                "curl",
                "--disable",
                "--silent",
                "--noproxy",
                "*",
                *self._interface_options,
                "--connect-timeout",
                "10",
                "--max-time",
                "30",
                "--header",
                "@-",
                "--data-binary",
                "@" + str(pending.resolve()),
                "--output",
                os.devnull,
                "--write-out",
                "%{http_code}",
                url,
            ],
            input=self._headers,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=35,
            check=False,
        )
        if response.returncode == 0 and response.stdout in {"200", "201"}:
            pending.unlink(missing_ok=True)
            return
        logger.warning(
            "Cooking cycle %s remains queued (curl %d, HTTP %s)",
            pending.stem,
            response.returncode,
            response.stdout or "unknown",
        )

    def _run(self):
        while True:
            self._wake.clear()
            try:
                for pending in sorted(self._spool.glob("*.json")):
                    self._upload(pending)
            except (OSError, subprocess.TimeoutExpired):
                logger.exception("Could not process the oven metrics queue")
            self._wake.wait(60)
