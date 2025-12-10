import json
import os
from hmi_consts import SETTINGS_DIR, SETTINGS_FILE


def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            pass
    return {}


def restore_saved_fan_delay_settings(shared_data: dict):
    settings = load_settings()
    fd = settings.get("fan_delay", {})
    tp = shared_data.get("time_page", {})
    if "minute" in tp:
        tp["minute"].set(int(fd.get("minute", 1)))
    if "second" in tp:
        tp["second"].set(int(fd.get("second", 1)))


def save_settings(minute: int, second: int) -> None:
    """
    Merge-only write: keep other fields (e.g., alarm_level) intact.
    Writes fan delay under data['fan_delay'] = {'minute':..., 'second':...}
    """
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    data = load_settings()
    data["fan_delay"] = {
        "minute": int(minute),
        "second": int(second),
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)
