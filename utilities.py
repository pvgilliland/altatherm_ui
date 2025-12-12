from datetime import datetime
import getpass
import json
import logging
from pathlib import Path
import platform
import shutil
import subprocess
from typing import Any, Dict, List, Optional
import psutil
import os
import re
from hmi_logger import setup_logging, get_log_file
from hmi_consts import SETTINGS_DIR

logger = logging.getLogger("utilities")


def _contains_digit(s: str) -> bool:
    return any(ch.isdigit() for ch in s)


def _to_int(x) -> Optional[int]:
    try:
        return int(x)
    except Exception:
        try:
            # Some tools emit strings like "123B" or "59.5G" -> best effort
            s = str(x).strip().upper()
            mult = 1
            for suf, m in (("K", 1024), ("M", 1024**2), ("G", 1024**3), ("T", 1024**4)):
                if s.endswith(suf):
                    mult = m
                    s = s[:-1]
                    break
            return int(float(s) * mult)
        except Exception:
            return None


# ---------- Linux (lsblk -J -O) ----------
def _linux_lsblk(only_usb: bool) -> List[Dict[str, Any]]:
    """
    Return a flat list of block devices/partitions from lsblk with key fields.
    Includes vendor/model (inherited to children when missing) so callers can filter.
    """
    if not shutil.which("lsblk"):
        raise RuntimeError("lsblk not found")

    # -J JSON, -O all attributes, -b bytes
    cp = subprocess.run(["lsblk", "-J", "-O", "-b"], capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr or "lsblk failed")

    data = json.loads(cp.stdout)
    out: List[Dict[str, Any]] = []

    def walk(node, parent_path=None, parent_vendor="", parent_model=""):
        name = node.get("name")
        path = f"/dev/{name}" if name else None
        tran = (node.get("tran") or node.get("transport") or "").lower()
        hotplug = bool(node.get("hotplug"))
        rm = bool(node.get("rm"))  # removable flag
        usb = (tran == "usb") or ((node.get("subsystems") or "").find("usb") >= 0)
        size = _to_int(node.get("size"))
        vendor = (node.get("vendor") or parent_vendor) or ""
        model = (node.get("model") or parent_model) or ""
        serial = node.get("serial")
        fstype = node.get("fstype")
        mp = node.get("mountpoint")
        is_mounted = bool(mp)
        tp = node.get("type")  # "disk", "part", "rom", "loop"...
        is_system = bool(node.get("ro"))  # heuristic

        rec = {
            "os": "linux",
            "type": tp,
            "name": name,
            "path": path,
            "size_bytes": size,
            "vendor": vendor,
            "model": model,
            "serial": serial,
            "is_usb": usb,
            "is_removable": rm or hotplug or usb,
            "is_system": is_system,
            "is_mounted": is_mounted,
            "fs_type": fstype,
            "mountpoints": [mp] if mp else [],
        }
        if not only_usb or usb:
            out.append(rec)

        for ch in node.get("children") or []:
            # pass down vendor/model so partitions inherit parent identity
            walk(ch, path, vendor, model)

    for blk in data.get("blockdevices", []):
        walk(blk)

    return out


def _win_get_volume_label(root: str) -> Optional[str]:
    """
    Return the Windows volume label for a drive root like 'E:\\'.
    Uses ctypes so we don't require pywin32.
    """
    try:
        import ctypes
        from ctypes import wintypes

        GetVolumeInformationW = ctypes.windll.kernel32.GetVolumeInformationW
        vol_name_buf = ctypes.create_unicode_buffer(261)
        fs_name_buf = ctypes.create_unicode_buffer(261)
        ser_num = wintypes.DWORD()
        max_comp_len = wintypes.DWORD()
        file_sys_flags = wintypes.DWORD()

        rc = GetVolumeInformationW(
            ctypes.c_wchar_p(root),
            vol_name_buf,
            len(vol_name_buf),
            ctypes.byref(ser_num),
            ctypes.byref(max_comp_len),
            ctypes.byref(file_sys_flags),
            fs_name_buf,
            len(fs_name_buf),
        )
        return vol_name_buf.value if rc else None
    except Exception:
        return None


def list_usb_drives() -> List[str]:
    """
    Returns a list of mountpoints for user-usable USB drives.
    Skips Microchip Curiosity devices:
      - Linux: vendor == 'Microchip' OR model contains 'Curiosity' (case-insensitive)
               Also skip if the mounted label's last path component is 'CURIOSITY'
      - Windows: skip removable drives with volume label 'CURIOSITY'
    On Linux, will attempt to mount the first unmounted USB partition under /media/<user>/USB_DRIVE.
    """
    mountpoints: List[str] = []
    system = platform.system()

    if system == "Linux":
        usb_list = _linux_lsblk(only_usb=True)
        source = ""
        for item in usb_list:
            if not all(k in item for k in ("path", "mountpoints", "is_mounted")):
                continue

            # --- Skip Microchip / Curiosity devices ---
            vendor = (item.get("vendor") or "").strip().lower()
            model = (item.get("model") or "").strip().lower()
            if vendor == "microchip" or "curiosity" in model:
                continue
            # If mounted, skip if the mountpoint label looks like CURIOSITY
            label_guess = ""
            if item["mountpoints"]:
                try:
                    label_guess = Path(item["mountpoints"][0]).name.strip().lower()
                except Exception:
                    label_guess = ""
            if label_guess == "curiosity":
                continue
            # -----------------------------------------

            # keep only partitions like /dev/sda1, /dev/sdb1, etc.
            if _contains_digit(item["path"]):
                if not item["is_mounted"]:
                    source = item["path"]
                    mountpoints.append(f"/media/{getpass.getuser()}/USB_DRIVE")
                else:
                    source = item["path"]
                    mountpoints.append(item["mountpoints"][0])

        # If we found a target mountpoint that isn't mounted, try to mount it
        if mountpoints:
            target_mp = Path(mountpoints[0])
            # target_mp.mkdir(parents=True, exist_ok=True)
            subprocess.run(["sudo", "mkdir", "-p", str(target_mp)], check=True)
            uid = os.getuid()
            gid = os.getgid()
            # Note: source will be last iterated candidate; here we intend to mount the first drive we picked
            # so recompute a suitable "source" from the usb_list that corresponds to mountpoints[0] if needed.
            try:
                subprocess.run(
                    [
                        "sudo",
                        "mount",
                        "-o",
                        f"uid={uid},gid={gid}",
                        source,
                        str(target_mp),
                    ],
                    check=False,
                )
            except Exception:
                pass

    elif system == "Windows":
        # On Windows, collect removable drives, skip ones labeled CURIOSITY
        for part in psutil.disk_partitions(all=True):
            # Typical removable drives have 'removable' in opts
            opts = (part.opts or "").lower()
            if "removable" not in opts:
                continue
            root = part.mountpoint  # e.g., 'E:\\'
            label = (_win_get_volume_label(root) or "").strip().upper()
            if label == "CURIOSITY":
                continue
            mountpoints.append(root)

    else:
        # Unsupported OS
        pass

    return mountpoints


def merge_rotated_logs(log_file: str | Path, out_dir: str | Path | None = None) -> Path:
    """
    Merge RotatingFileHandler logs into a single chronological file,
    and save with a timestamped filename: <stem>_<YYYY-mm-dd_HH-MM-SS><suffix>

    Order merged: oldest -> newest
      e.g., hmi.log.5 ... hmi.log.2, hmi.log.1, hmi.log
    """
    log_file = Path(log_file)
    if out_dir is None:
        out_dir = log_file.parent
    out_dir = Path(out_dir)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_file = out_dir / f"{log_file.stem}_{timestamp}{log_file.suffix}"

    # Find numbered rotations
    rx_num = re.compile(r"\.(\d+)$")
    numbered = []
    for p in log_file.parent.glob(f"{log_file.name}.*"):
        m = rx_num.search(p.name)
        if m:
            try:
                n = int(m.group(1))
                numbered.append((n, p))
            except ValueError:
                pass

    # Higher numbers are older -> reverse sort for oldest->newest
    numbered.sort(key=lambda t: t[0], reverse=True)

    to_read = [p for _, p in numbered] + [log_file]

    with out_file.open("w", encoding="utf-8") as out:
        for p in to_read:
            if p.exists():
                with p.open("r", encoding="utf-8", errors="ignore") as f:
                    out.write(f.read())
                    out.write("\n")

    return out_file


# returns False if no thumb drive present to save to
def save_log_file() -> tuple[bool, str]:
    """
    Merge current + rotated logs (timestamped output) and copy onto
    the first eligible USB mountpoint, skipping Microchip Curiosity devices.
    """
    mountpoints = list_usb_drives()
    if not mountpoints:
        return False, "E0001, No thumb drive detected"

    logFile = get_log_file()
    print(logFile)
    if not logFile or not Path(logFile).exists():
        return False, "Log file does not exist yet"

    # Merge logs next to the original log first
    mergedLogs = merge_rotated_logs(logFile, Path(logFile).parent)

    # Destination: if mountpoint is a directory, place the merged filename inside it
    dst_dir = Path(mountpoints[0])
    destination = dst_dir / mergedLogs.name if dst_dir.is_dir() else dst_dir

    try:
        shutil.copy2(mergedLogs, dst_dir)
        # Clean up the temporary merged file
        Path(mergedLogs).unlink(missing_ok=True)
        msg = f"Copied log file to {destination}"
        logger.info(msg)
        return True, msg
    except FileNotFoundError:
        msg = f"Log file not found: {logFile}"
    except PermissionError:
        msg = f"Permission denied copying to {destination}"
    except OSError as e:
        msg = f"OS error while copying log file: {e}"

    logger.error(msg)
    return False, msg


def load_use_sound_from_settings(default: bool = True) -> bool:
    path = os.path.join(SETTINGS_DIR, "settings.alt")
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            v = data.get("use_sound", default)
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return bool(v)
            if isinstance(v, str):
                return v.strip().lower() in ("1", "true", "yes", "y", "on")
    except Exception:
        pass
    return default


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    setup_logging("hmi")
    logger.info("Testing log export...")
    ok, message = save_log_file()
    print(ok, message)
